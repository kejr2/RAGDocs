from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue


@dataclass
class RetrievalResult:
    content: str
    metadata: Dict
    score: float
    source_type: str


class HybridRetriever:
    """Hybrid retriever with reranking for text and code collections"""
    
    def __init__(self, text_model: SentenceTransformer, code_model: SentenceTransformer, 
                 qdrant_client: QdrantClient):
        self.text_model = text_model
        self.code_model = code_model
        self.qdrant_client = qdrant_client
    
    def detect_query_type(self, query: str) -> str:
        """
        Detect if query is about code or text using keyword analysis
        and semantic similarity.
        """
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
        
        # Check for code-like patterns
        if any(pattern in query_lower for pattern in ['```', 'def ', 'function ', 'class ', '()', '{}']):
            code_score += 3
        
        # If scores are equal or both low, default to hybrid
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
        # Embed query
        query_embedding = model.encode([query])[0].tolist()
        
        # Build filter
        query_filter = None
        if doc_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
        
        # Query collection
        results = self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=top_k
        )
        
        retrieved = []
        for result in results:
            payload = result.payload
            # Qdrant returns distance (lower is better), convert to similarity
            distance = result.score
            score = 1 / (1 + distance) if distance > 0 else 1.0  # Convert distance to similarity score
            
            retrieved.append(RetrievalResult(
                content=payload.get("content", ""),
                metadata=payload,
                score=score,
                source_type=payload.get('type', 'unknown')
            ))
        
        return retrieved
    
    def rerank_results(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Rerank results using cross-encoder or other reranking strategy.
        For now, uses a simple relevance boosting based on keywords.
        """
        query_terms = set(query.lower().split())
        
        for result in results:
            content_terms = set(result.content.lower().split())
            
            # Calculate term overlap
            overlap = len(query_terms.intersection(content_terms))
            overlap_score = overlap / len(query_terms) if query_terms else 0
            
            # Boost score based on overlap
            result.score = result.score * 0.7 + overlap_score * 0.3
            
            # Boost code results if query seems code-related
            if result.source_type == "code" and any(
                kw in query.lower() for kw in ['code', 'function', 'implement', 'example']
            ):
                result.score *= 1.2
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def hybrid_retrieve(
        self,
        query: str,
        top_k: int = 10,
        doc_id: Optional[str] = None,
        code_weight: float = 0.5
    ) -> List[RetrievalResult]:
        """
        Perform hybrid retrieval from both text and code collections.
        Merges and reranks results.
        """
        query_type = self.detect_query_type(query)
        
        all_results = []
        
        if query_type == "code":
            # Primarily retrieve from code collection
            code_results = self.retrieve_from_collection(
                query, "code_chunks", self.code_model,
                top_k=int(top_k * 0.8), doc_id=doc_id
            )
            text_results = self.retrieve_from_collection(
                query, "text_chunks", self.text_model,
                top_k=int(top_k * 0.2), doc_id=doc_id
            )
            all_results = code_results + text_results
            
        elif query_type == "text":
            # Primarily retrieve from text collection
            text_results = self.retrieve_from_collection(
                query, "text_chunks", self.text_model,
                top_k=int(top_k * 0.8), doc_id=doc_id
            )
            code_results = self.retrieve_from_collection(
                query, "code_chunks", self.code_model,
                top_k=int(top_k * 0.2), doc_id=doc_id
            )
            all_results = text_results + code_results
            
        else:  # hybrid
            # Retrieve equally from both
            text_results = self.retrieve_from_collection(
                query, "text_chunks", self.text_model,
                top_k=int(top_k * 0.5), doc_id=doc_id
            )
            code_results = self.retrieve_from_collection(
                query, "code_chunks", self.code_model,
                top_k=int(top_k * 0.5), doc_id=doc_id
            )
            all_results = text_results + code_results
        
        # Rerank merged results
        reranked = self.rerank_results(query, all_results)
        
        # Return top_k results
        return reranked[:top_k]
    
    def get_context_window(
        self,
        results: List[RetrievalResult],
        max_tokens: int = 3000
    ) -> str:
        """
        Build context window from results, respecting token limit.
        Approximate tokens as words * 1.3.
        """
        context_parts = []
        current_tokens = 0
        
        for i, result in enumerate(results):
            # Estimate tokens
            estimated_tokens = int(len(result.content.split()) * 1.3)
            
            if current_tokens + estimated_tokens > max_tokens:
                break
            
            # Format context with metadata
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
    """Simple in-memory cache for query results."""
    
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size
        self.access_count = {}
    
    def _make_key(self, query: str, doc_id: Optional[str]) -> str:
        """Create cache key from query and doc_id."""
        import hashlib
        key_str = f"{query}:{doc_id or 'all'}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, query: str, doc_id: Optional[str] = None) -> Optional[List[RetrievalResult]]:
        """Retrieve from cache."""
        key = self._make_key(query, doc_id)
        if key in self.cache:
            self.access_count[key] = self.access_count.get(key, 0) + 1
            return self.cache[key]
        return None
    
    def set(self, query: str, results: List[RetrievalResult], doc_id: Optional[str] = None):
        """Store in cache with LFU eviction."""
        key = self._make_key(query, doc_id)
        
        # Evict least frequently used if at capacity
        if len(self.cache) >= self.max_size and self.access_count:
            lfu_key = min(self.access_count.items(), key=lambda x: x[1])[0]
            del self.cache[lfu_key]
            del self.access_count[lfu_key]
        
        self.cache[key] = results
        self.access_count[key] = 1
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.access_count.clear()

