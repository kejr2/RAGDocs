import logging
import time
from typing import List, Dict, Optional, Any
from sentence_transformers import SentenceTransformer, CrossEncoder
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    content: str
    metadata: Dict
    score: float
    source_type: str


class HybridRetriever:
    """Hybrid retriever with cross-encoder reranking for text and code collections."""

    def __init__(self, text_model: SentenceTransformer, code_model: SentenceTransformer,
                 qdrant_client: QdrantClient):
        self.text_model = text_model
        self.code_model = code_model
        self.qdrant_client = qdrant_client
        try:
            self.cross_encoder = CrossEncoder('BAAI/bge-reranker-base')
            logger.info("Cross-encoder reranker loaded: BAAI/bge-reranker-base")
        except Exception as e:
            logger.warning("Failed to load cross-encoder, falling back to heuristic reranking: %s", e)
            self.cross_encoder = None

    def detect_query_type(self, query: str) -> str:
        """Detect if query is about code or text using keyword analysis."""
        code_keywords = {
            'function', 'class', 'method', 'import', 'export', 'def', 'async',
            'const', 'let', 'var', 'return', 'api', 'endpoint', 'code',
            'implementation', 'syntax', 'error', 'exception', 'debug',
            'variable', 'parameter', 'argument', 'loop', 'condition',
            'algorithm', 'data structure', 'array', 'object', 'string'
        }
        text_keywords = {
            'explain', 'what', 'why', 'how', 'describe', 'overview',
            'introduction', 'concept', 'theory', 'background', 'summary',
            'documentation', 'guide', 'tutorial', 'example'
        }

        query_lower = query.lower()
        code_score = sum(1 for kw in code_keywords if kw in query_lower)
        text_score = sum(1 for kw in text_keywords if kw in query_lower)

        if any(pattern in query_lower for pattern in ['```', 'def ', 'function ', 'class ', '()', '{}']):
            code_score += 3

        if code_score > text_score:
            return "code"
        elif text_score > code_score:
            return "text"
        else:
            return "hybrid"

    def retrieve_from_collection(
        self,
        query: str,
        collection_name: str,
        model: SentenceTransformer,
        top_k: int = 10,
        doc_id: Optional[str] = None
    ) -> List[RetrievalResult]:
        """Retrieve relevant chunks from a single Qdrant collection."""
        query_embedding = model.encode([query])[0].tolist()

        query_filter = None
        if doc_id:
            query_filter = Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            )

        results = self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=top_k
        )

        retrieved = []
        for result in results:
            payload = result.payload
            # Qdrant COSINE returns score in [0,1] range (higher = more similar)
            score = result.score
            retrieved.append(RetrievalResult(
                content=payload.get("content", ""),
                metadata=payload,
                score=score,
                source_type=payload.get('type', 'unknown')
            ))

        return retrieved

    def rerank_results(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Rerank results using BAAI/bge-reranker-base cross-encoder.
        Falls back to term-overlap heuristic if cross-encoder is unavailable.
        """
        if not results:
            return results

        if self.cross_encoder is not None:
            try:
                pairs = [(query, r.content) for r in results]
                scores = self.cross_encoder.predict(pairs)
                for result, score in zip(results, scores):
                    result.score = float(score)
                results.sort(key=lambda x: x.score, reverse=True)
                logger.debug("Cross-encoder reranked %d results", len(results))
                return results
            except Exception as e:
                logger.warning("Cross-encoder reranking failed, falling back to heuristic: %s", e)

        # Heuristic fallback
        query_terms = set(query.lower().split())
        for result in results:
            content_terms = set(result.content.lower().split())
            overlap = len(query_terms.intersection(content_terms))
            overlap_score = overlap / len(query_terms) if query_terms else 0
            result.score = result.score * 0.7 + overlap_score * 0.3
            if result.source_type == "code" and any(
                kw in query.lower() for kw in ['code', 'function', 'implement', 'example']
            ):
                result.score *= 1.2

        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def hybrid_retrieve(
        self,
        query: str,
        top_k: int = 10,
        doc_id: Optional[str] = None,
        code_weight: float = 0.5
    ) -> List[RetrievalResult]:
        """Perform hybrid retrieval from both text and code collections."""
        query_type = self.detect_query_type(query)
        all_results = []

        if query_type == "code":
            code_results = self.retrieve_from_collection(
                query, "code_chunks", self.code_model, top_k=int(top_k * 0.8), doc_id=doc_id
            )
            text_results = self.retrieve_from_collection(
                query, "text_chunks", self.text_model, top_k=int(top_k * 0.2), doc_id=doc_id
            )
            all_results = code_results + text_results
        elif query_type == "text":
            text_results = self.retrieve_from_collection(
                query, "text_chunks", self.text_model, top_k=int(top_k * 0.8), doc_id=doc_id
            )
            code_results = self.retrieve_from_collection(
                query, "code_chunks", self.code_model, top_k=int(top_k * 0.2), doc_id=doc_id
            )
            all_results = text_results + code_results
        else:
            text_results = self.retrieve_from_collection(
                query, "text_chunks", self.text_model, top_k=int(top_k * 0.5), doc_id=doc_id
            )
            code_results = self.retrieve_from_collection(
                query, "code_chunks", self.code_model, top_k=int(top_k * 0.5), doc_id=doc_id
            )
            all_results = text_results + code_results

        reranked = self.rerank_results(query, all_results)
        return reranked[:top_k]

    def get_context_window(
        self,
        results: List[RetrievalResult],
        max_tokens: int = 3000
    ) -> str:
        """Build context window from results, respecting token limit."""
        context_parts = []
        current_tokens = 0

        for i, result in enumerate(results):
            estimated_tokens = int(len(result.content.split()) * 1.3)
            if current_tokens + estimated_tokens > max_tokens:
                break

            heading = result.metadata.get('heading', '')
            source_type = result.metadata.get('type', 'text')
            language = result.metadata.get('language', '')

            context_part = f"[Source {i+1}"
            if heading:
                context_part += f" - {heading}"
            if source_type == "code" and language:
                context_part += f" - {language} code"
            context_part += f"]\n{result.content}\n"

            context_parts.append(context_part)
            current_tokens += estimated_tokens

        return "\n---\n\n".join(context_parts)


class QueryCache:
    """In-memory LFU+TTL cache for full query responses.

    Eviction priority:
      1. Expired entries (age > ttl) are purged on every write.
      2. When still at capacity, the least-frequently-used entry is evicted.
    """

    def __init__(self, max_size: int = 500, ttl: int = 3600):
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.ttl = ttl  # seconds
        self.access_count: Dict[str, int] = {}
        self.timestamps: Dict[str, float] = {}

    def _make_key(self, query: str, doc_id: Optional[str]) -> str:
        import hashlib
        key_str = f"{query}:{doc_id or 'all'}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, ts in self.timestamps.items() if now - ts > self.ttl]
        for k in expired:
            self.cache.pop(k, None)
            self.access_count.pop(k, None)
            self.timestamps.pop(k, None)
        if expired:
            logger.debug("Evicted %d expired cache entries", len(expired))

    def get(self, query: str, doc_id: Optional[str] = None) -> Optional[Any]:
        key = self._make_key(query, doc_id)
        if key not in self.cache:
            return None
        if time.time() - self.timestamps.get(key, 0) > self.ttl:
            # Stale entry — remove and miss
            self.cache.pop(key, None)
            self.access_count.pop(key, None)
            self.timestamps.pop(key, None)
            return None
        self.access_count[key] = self.access_count.get(key, 0) + 1
        logger.debug("Cache hit for query: %s", query[:60])
        return self.cache[key]

    def set(self, query: str, response: Any, doc_id: Optional[str] = None):
        key = self._make_key(query, doc_id)
        self._evict_expired()
        if len(self.cache) >= self.max_size and self.access_count:
            lfu_key = min(self.access_count.items(), key=lambda x: x[1])[0]
            self.cache.pop(lfu_key, None)
            self.access_count.pop(lfu_key, None)
            self.timestamps.pop(lfu_key, None)
        self.cache[key] = response
        self.access_count[key] = 1
        self.timestamps[key] = time.time()
        logger.debug("Cached response for query: %s", query[:60])

    def clear(self):
        self.cache.clear()
        self.access_count.clear()
        self.timestamps.clear()
