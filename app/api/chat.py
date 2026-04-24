import logging
import json
import os
import time
from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from qdrant_client.models import Filter, FieldCondition, MatchValue
import asyncio
from concurrent.futures import ThreadPoolExecutor
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client, ensure_collection_exists
from app.services.embeddings import embedding_service
from app.services.gemini import gemini_service
from app.services.query_enhancer import query_enhancer
from app.services.answer_formatter import format_basic_answer
from app.services.retrieval import QueryCache
from app.services.metrics import log_query, record_feedback
from app.services.guards import validate_query
from app.services.conversations import (
    create_conversation,
    add_turn,
    get_recent_turns,
    get_full_conversation,
    soft_delete_conversation,
    ENHANCER_TURN_WINDOW,
)

# BM25 hybrid retrieval (Fix 4) — graceful import
try:
    from rank_bm25 import BM25Okapi as _BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25Okapi = None
    _BM25_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Thread pool for parallel CPU-bound operations
_executor = ThreadPoolExecutor(max_workers=int(os.getenv("WORKER_THREADS", "4")))

# Module-level query cache: 500 entries, 1-hour TTL
query_cache = QueryCache(max_size=500, ttl=3600)

FALLBACK_SCORE_THRESHOLD = 0.30     # combined BM25+vector score; raw cosine alone is typically 0.25-0.50
SECTION_FALLBACK_THRESHOLD = 0.55   # below this → try section-filtered pass (Fix 5)
FALLBACK_MESSAGE = (
    "I couldn't find a confident answer in your documentation. "
    "Try rephrasing or check if this topic is covered in your uploaded docs."
)


# ---------------------------------------------------------------------------
# BM25 hybrid re-ranking helper (Fix 4)
# ---------------------------------------------------------------------------

def _bm25_hybrid_rerank(
    query: str,
    results: list,
    bm25_weight: float = 0.4,
    vec_weight: float = 0.6,
) -> List[tuple]:
    """
    Re-rank *results* (Qdrant ScoredPoints) using a hybrid of BM25 keyword
    score (weight 0.4) and cosine vector score (weight 0.6).

    Returns List[(combined_score: float, result)] sorted highest-first.
    The combined_score is in [0, 1] and should be used for threshold checks
    so that keyword-rich chunks with middling vector scores still surface.

    If rank_bm25 is not installed, returns [(result.score, result)] pairs
    sorted by original Qdrant score.
    """
    if not results:
        return []

    if not _BM25_AVAILABLE:
        return sorted([(r.score, r) for r in results], key=lambda x: x[0], reverse=True)

    try:
        # Use word-boundary tokenisation so pipe-table cells like |204|No
        # are split into ["204", "no"] instead of staying as "|204|no"
        import re as _re
        _tok = lambda t: _re.findall(r'\b\w+\b', t.lower())
        corpus = [_tok(r.payload.get("content", "")) for r in results]
        bm25 = _BM25Okapi(corpus)
        query_tokens = _tok(query)
        bm25_scores = bm25.get_scores(query_tokens)

        # Normalise both score families to [0, 1]
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
        bm25_norm = [s / max_bm25 for s in bm25_scores]

        vec_raw = [r.score for r in results]
        max_vec = max(vec_raw) if max(vec_raw) > 0 else 1.0
        vec_norm = [s / max_vec for s in vec_raw]

        combined = sorted(
            [
                (bm25_weight * b + vec_weight * v, r)
                for b, v, r in zip(bm25_norm, vec_norm, results)
            ],
            key=lambda x: x[0],
            reverse=True,
        )
        return combined

    except Exception:
        # Never crash the pipeline over BM25
        return sorted([(r.score, r) for r in results], key=lambda x: x[0], reverse=True)


# ---------------------------------------------------------------------------
# Document diversity helper (Issue 1, Fix A)
# ---------------------------------------------------------------------------

def _diversify_by_document(
    reranked_pairs: List[tuple],
    target_k: int = 8,
    max_per_doc: int = 3,
    min_docs: int = 2,
    min_score_for_min_docs: float = 0.5,
) -> List[tuple]:
    """
    Re-order BM25-hybrid output to prevent any single document from dominating
    the top-k. Keeps reranked_pairs' (combined_score, result) shape.

    Strategy:
      1. Group by doc_id, preserving descending-score order within each group.
      2. Round-robin across docs, taking up to max_per_doc per doc.
      3. If the chosen top-k contains fewer than min_docs distinct documents
         AND at least min_docs docs have a chunk scoring >= min_score_for_min_docs,
         swap in the best chunk from each missing doc (displacing the lowest-
         scored over-represented chunk).

    If reranked_pairs has only one source document, returns the input slice
    unchanged (nothing to diversify).
    """
    if not reranked_pairs:
        return []

    # Group, preserving original sort
    by_doc: Dict[str, List[tuple]] = {}
    for pair in reranked_pairs:
        _, r = pair
        doc_id = (r.payload or {}).get("doc_id") or "__unknown__"
        by_doc.setdefault(doc_id, []).append(pair)

    if len(by_doc) <= 1:
        return reranked_pairs[:target_k]

    # Round-robin pick
    queues = {d: list(pairs) for d, pairs in by_doc.items()}
    taken_per_doc: Dict[str, int] = {d: 0 for d in queues}
    selected: List[tuple] = []

    # Order docs by their best score so the highest-quality doc gets first pick
    doc_order = sorted(queues.keys(), key=lambda d: queues[d][0][0], reverse=True)

    while len(selected) < target_k:
        progress = False
        for d in doc_order:
            if len(selected) >= target_k:
                break
            if taken_per_doc[d] >= max_per_doc:
                continue
            if not queues[d]:
                continue
            selected.append(queues[d].pop(0))
            taken_per_doc[d] += 1
            progress = True
        if not progress:
            # All docs are at max_per_doc or empty — backfill with leftovers,
            # ignoring max_per_doc so we still hit target_k.
            leftovers = [p for d in doc_order for p in queues[d]]
            leftovers.sort(key=lambda x: x[0], reverse=True)
            for p in leftovers:
                if len(selected) >= target_k:
                    break
                selected.append(p)
            break

    # Min-docs guarantee
    distinct_in_selected = {(_r.payload or {}).get("doc_id") for _, _r in selected}
    qualified_docs = {
        d for d, pairs in by_doc.items()
        if pairs and pairs[0][0] >= min_score_for_min_docs
    }
    if len(distinct_in_selected) < min_docs and len(qualified_docs) >= min_docs:
        missing = [d for d in qualified_docs if d not in distinct_in_selected]
        # Sort missing docs by their top score
        missing.sort(key=lambda d: by_doc[d][0][0], reverse=True)
        for d in missing:
            if not by_doc[d]:
                continue
            # Drop the lowest-scored selected chunk from the most over-represented doc
            over_doc = max(
                distinct_in_selected,
                key=lambda x: sum(1 for _, _r in selected if (_r.payload or {}).get("doc_id") == x),
            )
            # Find the lowest-scored entry from over_doc
            victim_idx = None
            for i in range(len(selected) - 1, -1, -1):
                if (selected[i][1].payload or {}).get("doc_id") == over_doc:
                    victim_idx = i
                    break
            if victim_idx is None:
                continue
            selected[victim_idx] = by_doc[d][0]
            distinct_in_selected = {(_r.payload or {}).get("doc_id") for _, _r in selected}
            if len(distinct_in_selected) >= min_docs:
                break

    # Final sort by combined_score so the top of the list is still the best chunk
    selected.sort(key=lambda x: x[0], reverse=True)
    return selected


# ---------------------------------------------------------------------------
# Intent-based doc affinity (Issue 2, Fix B)
# ---------------------------------------------------------------------------

# For each intent, list filename substrings (case-insensitive) we want to
# guarantee at least min_each chunks from when they exist in the candidate pool.
INTENT_DOC_AFFINITY: Dict[str, List[str]] = {
    "getting_started":  ["auth", "api_reference", "api reference"],
    "authentication":   ["auth"],
    "webhooks":         ["webhook"],
    "api_usage":        ["api_reference", "api reference"],
    "error_handling":   ["api_reference", "webhook"],
    "security":         ["auth", "security"],
    "general":          [],
}


def _apply_intent_affinity(
    reranked_pairs: List[tuple],
    intent: str,
    min_each: int = 2,
    target_k: int = 8,
) -> List[tuple]:
    """
    Make sure each intent-affine document has at least *min_each* chunks in
    the top-k slice, when chunks from that doc exist in the candidate pool.
    Operates on the full reranked_pairs (not just the top-k) so we have headroom
    to promote.
    """
    affine_substrs = [s.lower() for s in INTENT_DOC_AFFINITY.get(intent, [])]
    if not affine_substrs or not reranked_pairs:
        return reranked_pairs

    def matches_any(filename: str) -> Optional[str]:
        fl = (filename or "").lower()
        for s in affine_substrs:
            if s in fl:
                return s
        return None

    # Bucket pairs by which affinity key they match (first match wins).
    by_key: Dict[str, List[tuple]] = {s: [] for s in affine_substrs}
    other: List[tuple] = []
    for pair in reranked_pairs:
        _, r = pair
        key = matches_any((r.payload or {}).get("source_file", ""))
        if key is not None:
            by_key[key].append(pair)
        else:
            other.append(pair)

    head = list(reranked_pairs[:target_k])
    head_ids = {(_r.payload or {}).get("chunk_id", _r.id) for _, _r in head}

    for key, pool in by_key.items():
        if not pool:
            continue
        present = sum(
            1 for _, _r in head
            if matches_any((_r.payload or {}).get("source_file", "")) == key
        )
        needed = min_each - present
        if needed <= 0:
            continue
        # Pull the next-best chunks from this doc that aren't already in head.
        candidates = [p for p in pool if (p[1].payload or {}).get("chunk_id", p[1].id) not in head_ids]
        for cand in candidates[:needed]:
            # Displace the lowest-scored item in head that isn't already
            # satisfying another affinity key.
            displaceable = [
                (i, pair) for i, pair in enumerate(head)
                if matches_any((pair[1].payload or {}).get("source_file", "")) is None
            ]
            if not displaceable:
                # Everything in head is affine — displace lowest of the most
                # over-represented key.
                displaceable = list(enumerate(head))
            victim_idx, _ = min(displaceable, key=lambda x: x[1][0])
            head[victim_idx] = cand
            head_ids = {(_r.payload or {}).get("chunk_id", _r.id) for _, _r in head}

    head.sort(key=lambda x: x[0], reverse=True)
    # Append the rest (untouched tail) so callers that read further still work.
    head_ids = {(_r.payload or {}).get("chunk_id", _r.id) for _, _r in head}
    tail = [p for p in reranked_pairs if (p[1].payload or {}).get("chunk_id", p[1].id) not in head_ids]
    return head + tail


# ---------------------------------------------------------------------------
# Section-filtered fallback helper (Fix 5)
# ---------------------------------------------------------------------------

def _section_filtered_fallback(
    query_keywords: List[str],
    results: list,
    top_k: int,
) -> list:
    """
    If the top result's score is below SECTION_FALLBACK_THRESHOLD, filter the
    candidate pool to chunks whose *section_heading* contains at least one
    query keyword, then return up to *top_k* of those.

    Returns an empty list if no matching sections are found (caller will fall
    through to the hard-fallback message).
    """
    if not query_keywords:
        return []

    keywords_lower = [kw.lower() for kw in query_keywords if len(kw) > 2]
    if not keywords_lower:
        return []

    filtered = [
        r for r in results
        if any(
            kw in (r.payload.get("section_heading") or r.payload.get("heading") or "").lower()
            for kw in keywords_lower
        )
    ]
    return filtered[:top_k]


def _confidence_label(score: float) -> str:
    if score > 0.80:
        return "HIGH"
    if score >= 0.60:
        return "MEDIUM"
    return "LOW"


class QueryRequest(BaseModel):
    query: str
    doc_id: Optional[str] = None
    top_k: int = 10
    conversation_id: Optional[str] = None  # if absent, server creates a new one


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    context_used: List[str]
    confidence: str = "LOW"
    fallback_triggered: bool = False
    query_id: Optional[str] = None
    conversation_id: Optional[str] = None
    used_context: bool = False  # true iff prior turns influenced the rewrite


class FeedbackRequest(BaseModel):
    query_id: str
    feedback: int  # 1 = thumbs up, -1 = thumbs down


def _resolve_conversation(conversation_id: Optional[str]) -> tuple[str, list, bool]:
    """
    Resolve / create the conversation_id and return:
      (conversation_id, prior_turns, has_prior)
    prior_turns is the rolling window the enhancer will see.
    """
    if not conversation_id:
        return create_conversation(), [], False
    prior = get_recent_turns(conversation_id, n=ENHANCER_TURN_WINDOW)
    return conversation_id, prior, len(prior) > 0


def detect_query_type(query: str) -> str:
    """Detect if query is about code or general text."""
    code_keywords = ['function', 'class', 'method', 'import', 'def', 'async',
                     'const', 'let', 'var', 'return', 'api', 'endpoint',
                     'code', 'implementation', 'syntax']
    query_lower = query.lower()
    if any(keyword in query_lower for keyword in code_keywords):
        return "code"
    return "text"


async def generate_embeddings_parallel(query: str) -> tuple:
    """Generate text and code embeddings in parallel."""
    loop = asyncio.get_event_loop()
    text_task = loop.run_in_executor(_executor, lambda: embedding_service.encode_text([query])[0])
    code_task = loop.run_in_executor(_executor, lambda: embedding_service.encode_code([query])[0])
    text_embedding, code_embedding = await asyncio.gather(text_task, code_task)
    return text_embedding, code_embedding


async def search_collections_parallel(
    qdrant_client,
    text_embedding: List[float],
    code_embedding: List[float],
    text_dim: int,
    code_dim: int,
    query_filter: Optional[Filter],
    text_limit: int,
    code_limit: int,
    should_search_code: bool = True
) -> tuple:
    """Search text and code Qdrant collections in parallel."""
    loop = asyncio.get_event_loop()

    ensure_collection_exists("text_chunks", text_dim)
    if should_search_code:
        ensure_collection_exists("code_chunks", code_dim)

    text_task = loop.run_in_executor(
        _executor,
        lambda: qdrant_client.search(
            collection_name="text_chunks",
            query_vector=text_embedding,
            query_filter=query_filter,
            limit=text_limit
        )
    )

    code_task = None
    if should_search_code:
        code_task = loop.run_in_executor(
            _executor,
            lambda: qdrant_client.search(
                collection_name="code_chunks",
                query_vector=code_embedding,
                query_filter=query_filter,
                limit=code_limit
            )
        )

    text_results = await text_task
    code_results = await code_task if code_task else []
    return text_results, code_results


async def _run_rag_pipeline(request: QueryRequest) -> QueryResponse:
    """Core RAG pipeline shared by both /query and /stream endpoints."""
    total_start = time.time()

    # --- Conversation memory ---
    conversation_id, prior_turns, used_context = _resolve_conversation(request.conversation_id)

    # Persist the user turn before retrieval — even on fallback we want it logged.
    add_turn(conversation_id, "user", request.query)

    # --- Cache check (keyed by raw query — context-rewrites are cheap to redo)
    cached = query_cache.get(request.query, request.doc_id)
    if cached:
        logger.info("Cache hit for query: %s", request.query[:60])
        # Persist assistant turn from the cached answer so memory stays consistent.
        add_turn(conversation_id, "assistant", cached.answer, sources_used=cached.sources)
        # Return a shallow copy with conversation_id stamped in.
        return QueryResponse(
            **{**cached.dict(), "conversation_id": conversation_id, "used_context": used_context}
        )

    # Step 1a: Resolve pronouns / "it" using prior turns (if any).
    t0 = time.time()
    rewritten_query = query_enhancer.rewrite_with_context(request.query, prior_turns)
    if rewritten_query != request.query:
        logger.info("Context rewrite: %r → %r", request.query[:60], rewritten_query[:80])

    # Step 1b: Standard enhancement on the (possibly rewritten) query.
    logger.info("Processing query: %s", rewritten_query[:80])
    enhanced_data = query_enhancer.enhance_query(rewritten_query)
    intent = query_enhancer.classify_intent(rewritten_query)
    logger.info("Query enhancement: %.2fs (intent=%s)", time.time() - t0, intent)

    required_topics = enhanced_data.get("required_topics", [])
    recommended_top_k = enhanced_data.get("recommended_top_k", request.top_k)
    multi_query_needed = enhanced_data.get("multi_query_needed", False)
    effective_top_k = max(request.top_k, recommended_top_k)

    hybrid_search_query = query_enhancer.build_hybrid_search_query(enhanced_data, rewritten_query)
    query_type = detect_query_type(hybrid_search_query)

    qdrant_client = get_qdrant_client()
    query_filter = None
    if request.doc_id:
        query_filter = Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=request.doc_id))]
        )

    text_dim = embedding_service.get_text_embedding_dim()
    code_dim = embedding_service.get_code_embedding_dim()
    all_results = []

    # Step 2: Retrieval
    retrieval_start = time.time()
    if multi_query_needed and len(required_topics) > 1:
        logger.info("Multi-query mode: %d topics", len(required_topics))

        async def search_topic(topic: str):
            topic_query = f"{topic} {rewritten_query}"
            text_emb, code_emb = await generate_embeddings_parallel(topic_query)
            per_topic_k = effective_top_k // len(required_topics) + 2
            return await search_collections_parallel(
                qdrant_client, text_emb, code_emb, text_dim, code_dim,
                query_filter, per_topic_k, per_topic_k, should_search_code=True
            )

        topic_results = await asyncio.gather(*[search_topic(t) for t in required_topics])
        for text_res, code_res in topic_results:
            all_results.extend([(r, "text") for r in text_res])
            all_results.extend([(r, "code") for r in code_res])
    else:
        should_search_code = (
            query_type == "code" or
            enhanced_data.get("query_type") in ["example", "how-to", "multi-step"] or
            any(w in hybrid_search_query.lower() for w in
                ["what is", "what are", "explain", "describe", "define", "example", "code"])
        )
        text_embedding, code_embedding = await generate_embeddings_parallel(hybrid_search_query)
        # Fetch a larger candidate pool — BM25 then narrows it down.
        # Always include at least 15 code-chunk candidates even for non-code
        # queries: pymupdf4llm sometimes wraps text in ``` fences, mislabelling
        # otherwise-prose content as "code" chunks.
        text_limit = max(effective_top_k * 4, 40)
        code_limit = max(effective_top_k * 3, 30) if should_search_code else 15
        text_results, code_results = await search_collections_parallel(
            qdrant_client, text_embedding, code_embedding, text_dim, code_dim,
            query_filter, text_limit, code_limit, should_search_code
        )
        all_results.extend([(r, "text") for r in text_results])
        if should_search_code:
            all_results.extend([(r, "code") for r in code_results])

    retrieval_latency_ms = int((time.time() - retrieval_start) * 1000)
    logger.info("Retrieval: %.2fs, %d raw results", retrieval_latency_ms / 1000, len(all_results))

    # Step 3: BM25 hybrid re-ranking (Fix 4) + section-filtered fallback (Fix 5)
    query_keywords = enhanced_data.get("keywords", [])
    stop_words = {"what", "is", "are", "the", "for", "with", "from", "this", "that",
                  "how", "to", "do", "does", "should", "can", "will"}
    query_words = [w.lower() for w in rewritten_query.split() if len(w) > 3 and w.lower() not in stop_words]
    all_keywords = list(set([kw.lower() for kw in query_keywords] + query_words))

    # Deduplicate by chunk_id (multi-query can yield duplicates)
    seen_ids: set = set()
    unique_results = []
    for r, rtype in all_results:
        cid = r.payload.get("chunk_id", r.id)
        if cid not in seen_ids:
            seen_ids.add(cid)
            unique_results.append(r)

    # BM25 hybrid re-rank on the expanded candidate pool
    # Returns List[(combined_score, result)] — use combined_score for threshold
    reranked_pairs = _bm25_hybrid_rerank(hybrid_search_query, unique_results)

    # Document diversity (Issue 1, Fix A): prevent any one doc from dominating
    # the top-k. Only apply when the user hasn't filtered to a single doc.
    if not request.doc_id:
        reranked_pairs = _diversify_by_document(
            reranked_pairs,
            target_k=max(effective_top_k, 8),
            max_per_doc=3,
            min_docs=2,
        )
        # Intent-based affinity (Issue 2, Fix B): for getting_started etc.,
        # guarantee min_each chunks from intent-relevant docs when present.
        reranked_pairs = _apply_intent_affinity(
            reranked_pairs, intent,
            min_each=2, target_k=max(effective_top_k, 8),
        )

    # Keep a flat list of results for the section-filtered fallback
    reranked = [r for _, r in reranked_pairs]

    MIN_CONTENT_LEN = 10
    sources = []
    context_chunks = []

    for combined_score, result in reranked_pairs[:effective_top_k]:
        payload = result.payload
        content = payload.get("content", "").strip()
        heading = payload.get("heading", "").strip()
        chunk_type = payload.get("type", "text")

        if not content or len(content) < MIN_CONTENT_LEN:
            continue

        sources.append({
            "content": content,
            "metadata": {
                "chunk_id": payload.get("chunk_id"),
                "doc_id": payload.get("doc_id"),
                "source_file": payload.get("source_file"),
                "start": payload.get("start"),
                "end": payload.get("end"),
                "type": chunk_type,
                "heading": heading,
                "language": payload.get("language", ""),
                "page_number": payload.get("page_number", 0),
                "section_heading": payload.get("section_heading", ""),
                "has_table": payload.get("has_table", False),
                "has_list": payload.get("has_list", False),
            },
            "relevance_score": float(combined_score)   # BM25-enhanced score
        })
        context_chunks.append(f"{heading}\n{content}" if heading else content)

    # --- Confidence signal ---
    top_score = sources[0]["relevance_score"] if sources else 0.0
    confidence = _confidence_label(top_score)

    # --- Section-filtered fallback pass (Fix 5) ---
    # If confidence is below SECTION_FALLBACK_THRESHOLD but above the hard
    # floor, try a second pass restricted to chunks whose section_heading
    # contains a query keyword.
    if sources and FALLBACK_SCORE_THRESHOLD <= top_score < SECTION_FALLBACK_THRESHOLD:
        logger.info(
            "Section-filtered fallback pass (top_score=%.3f < %.2f)",
            top_score, SECTION_FALLBACK_THRESHOLD,
        )
        section_filtered = _section_filtered_fallback(
            all_keywords, reranked, effective_top_k
        )
        if section_filtered:
            # Re-rank the section-filtered subset with BM25 again
            sec_pairs = _bm25_hybrid_rerank(hybrid_search_query, section_filtered)
            new_sources: List[Dict] = []
            new_context: List[str] = []
            for combined_score, result in sec_pairs:
                payload = result.payload
                content = payload.get("content", "").strip()
                heading = payload.get("heading", "").strip()
                if not content or len(content) < MIN_CONTENT_LEN:
                    continue
                new_sources.append({
                    "content": content,
                    "metadata": {
                        "chunk_id": payload.get("chunk_id"),
                        "doc_id": payload.get("doc_id"),
                        "source_file": payload.get("source_file"),
                        "start": payload.get("start"),
                        "end": payload.get("end"),
                        "type": payload.get("type", "text"),
                        "heading": heading,
                        "language": payload.get("language", ""),
                        "page_number": payload.get("page_number", 0),
                        "section_heading": payload.get("section_heading", ""),
                        "has_table": payload.get("has_table", False),
                        "has_list": payload.get("has_list", False),
                    },
                    "relevance_score": float(combined_score),
                })
                new_context.append(f"{heading}\n{content}" if heading else content)
            if new_sources:
                sources = new_sources
                context_chunks = new_context
                top_score = sources[0]["relevance_score"]
                confidence = _confidence_label(top_score)
                logger.info(
                    "Section-filtered pass returned %d chunks (new top_score=%.3f)",
                    len(sources), top_score,
                )

    # --- Hard fallback if top score is below threshold ---
    if not context_chunks or top_score < FALLBACK_SCORE_THRESHOLD:
        fallback_msg = FALLBACK_MESSAGE if not context_chunks else (
            FALLBACK_MESSAGE if top_score < FALLBACK_SCORE_THRESHOLD else
            "I couldn't find relevant information to answer your question. "
            "Try rephrasing or checking that the document covers this topic."
        )
        logger.warning("Fallback triggered (top_score=%.3f) for: %s", top_score, request.query[:60])
        qid = log_query(
            query_text=request.query,
            chunks_retrieved=len(sources),
            retrieval_score=top_score,
            retrieval_latency_ms=retrieval_latency_ms,
            response_latency_ms=int((time.time() - total_start) * 1000),
            tokens_used=0,
            source_cited=False,
            fallback_triggered=True,
            model_used="gemini",
        )
        add_turn(conversation_id, "assistant", fallback_msg, sources_used=[])
        return QueryResponse(
            answer=fallback_msg,
            sources=[],
            context_used=[],
            confidence="LOW",
            fallback_triggered=True,
            query_id=qid,
            conversation_id=conversation_id,
            used_context=used_context,
        )

    max_ctx = min(10 if (multi_query_needed and len(required_topics) > 1) else 5, len(context_chunks))
    context = "\n\n---\n\n".join(context_chunks[:max_ctx])
    logger.info("Using %d context chunks out of %d filtered results", max_ctx, len(sources))

    # Step 4: Answer generation
    answer_start = time.time()
    tokens_used = 0
    tokens_in_count = 0
    tokens_out_count = 0
    if gemini_service.enabled:
        try:
            # Pass the rewritten query so the answer reflects the resolved
            # intent (e.g. "How do I rotate an API key?" instead of "rotate it?")
            answer, tokens_in_count, tokens_out_count = gemini_service.generate_answer(rewritten_query, context)
            tokens_used = tokens_in_count + tokens_out_count
        except Exception as e:
            logger.error("Gemini failed after retries: %s", e)
            answer = None
        if not answer or len(answer.strip()) < 10:
            answer = format_basic_answer(sources)
    else:
        answer = format_basic_answer(sources)

    response_latency_ms = int((time.time() - total_start) * 1000)
    logger.info("Answer generation: %.2fs | Total: %.2fs", time.time() - answer_start, response_latency_ms / 1000)

    # Detect hallucination-fallback phrases in the answer
    fallback_phrases = ["i don't know", "i don't have", "not found", "cannot find", "no information"]
    fallback_triggered = any(p in answer.lower() for p in fallback_phrases)

    qid = log_query(
        query_text=request.query,
        chunks_retrieved=len(sources),
        retrieval_score=top_score,
        retrieval_latency_ms=retrieval_latency_ms,
        response_latency_ms=response_latency_ms,
        tokens_used=tokens_used,
        tokens_in=tokens_in_count,
        tokens_out=tokens_out_count,
        source_cited=len(sources) > 0,
        fallback_triggered=fallback_triggered,
        model_used="gemini",
    )

    add_turn(conversation_id, "assistant", answer, sources_used=sources)

    response = QueryResponse(
        answer=answer,
        sources=sources,
        context_used=context_chunks,
        confidence=confidence,
        fallback_triggered=fallback_triggered,
        query_id=qid,
        conversation_id=conversation_id,
        used_context=used_context,
    )

    query_cache.set(request.query, response, request.doc_id)
    return response


@router.get("/models", status_code=status.HTTP_200_OK)
async def list_models():
    """Return available Gemini models for the frontend model selector."""
    models = [
        {"id": "gemini-2.5-flash",   "name": "Gemini 2.5 Flash",   "tier": "fast"},
        {"id": "gemini-2.5-pro",     "name": "Gemini 2.5 Pro",     "tier": "powerful"},
        {"id": "gemini-2.0-flash",   "name": "Gemini 2.0 Flash",   "tier": "fast"},
    ]
    return {"models": models, "default": "gemini-2.5-flash"}


@router.post("/query", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def query_chat(
    request: Request,
    body: QueryRequest,
    db: Session = Depends(get_db)
) -> QueryResponse:
    """Query the RAG assistant using hybrid retrieval with cross-encoder reranking."""
    is_safe, reason = validate_query(body.query)
    if not is_safe:
        raise HTTPException(status_code=400, detail=reason)
    try:
        return await _run_rag_pipeline(body)
    except Exception as e:
        logger.exception("Error in /chat/query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying document: {str(e)}"
        )


@router.post("/stream")
@limiter.limit("20/minute")
async def stream_chat(
    request: Request,
    body: QueryRequest,
    db: Session = Depends(get_db)
):
    """Stream answer tokens via Server-Sent Events (SSE).

    Events:
      - data: {"token": "..."}  — partial answer token
      - data: {"done": true, "sources": [...], "context_used": [...],
               "confidence": "HIGH|MEDIUM|LOW", "fallback_triggered": bool}
      - data: {"error": "..."}  — on failure
    """
    # Guard check before entering async generator
    is_safe, reason = validate_query(body.query)
    if not is_safe:
        raise HTTPException(status_code=400, detail=reason)

    async def event_generator():
        try:
            total_start = time.time()

            # --- Conversation memory ---
            conversation_id, prior_turns, used_context = _resolve_conversation(body.conversation_id)
            add_turn(conversation_id, "user", body.query)

            # Cache check
            cached = query_cache.get(body.query, body.doc_id)
            if cached:
                logger.info("Stream cache hit: %s", body.query[:60])
                chunk_size = 8
                answer = cached.answer
                for i in range(0, len(answer), chunk_size):
                    yield {"data": json.dumps({"token": answer[i:i+chunk_size]})}
                    await asyncio.sleep(0)
                add_turn(conversation_id, "assistant", answer, sources_used=cached.sources)
                yield {"data": json.dumps({
                    "done": True,
                    "sources": cached.sources,
                    "context_used": cached.context_used,
                    "confidence": cached.confidence,
                    "fallback_triggered": cached.fallback_triggered,
                    "conversation_id": conversation_id,
                    "used_context": used_context,
                    "prior_turn_count": len(prior_turns),
                })}
                return

            # Resolve pronouns / "it" using prior turns.
            rewritten_query = query_enhancer.rewrite_with_context(body.query, prior_turns)
            if rewritten_query != body.query:
                logger.info("Stream context rewrite: %r → %r", body.query[:60], rewritten_query[:80])

            enhanced_data = query_enhancer.enhance_query(rewritten_query)
            intent = query_enhancer.classify_intent(rewritten_query)
            hybrid_search_query = query_enhancer.build_hybrid_search_query(enhanced_data, rewritten_query)
            query_type = detect_query_type(hybrid_search_query)

            qdrant_client = get_qdrant_client()
            query_filter = None
            if body.doc_id:
                query_filter = Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=body.doc_id))]
                )

            text_dim = embedding_service.get_text_embedding_dim()
            code_dim = embedding_service.get_code_embedding_dim()
            effective_top_k = max(body.top_k, enhanced_data.get("recommended_top_k", body.top_k))

            should_search_code = (
                query_type == "code" or
                enhanced_data.get("query_type") in ["example", "how-to", "multi-step"] or
                any(w in hybrid_search_query.lower() for w in
                    ["explain", "describe", "define", "example", "code"])
            )

            retrieval_start = time.time()
            text_embedding, code_embedding = await generate_embeddings_parallel(hybrid_search_query)
            text_results, code_results = await search_collections_parallel(
                qdrant_client, text_embedding, code_embedding, text_dim, code_dim,
                query_filter, max(effective_top_k * 4, 40),
                max(effective_top_k * 3, 30) if should_search_code else 15,
                True   # always search code collection
            )
            retrieval_latency_ms = int((time.time() - retrieval_start) * 1000)

            seen_ids: set = set()
            unique_stream = []
            for r, _ in [(r, "text") for r in text_results] + (
                [(r, "code") for r in code_results] if should_search_code else []
            ):
                cid = r.payload.get("chunk_id", r.id)
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    unique_stream.append(r)

            reranked_stream = _bm25_hybrid_rerank(hybrid_search_query, unique_stream)

            # Document diversity (Issue 1, Fix A)
            if not body.doc_id:
                reranked_stream = _diversify_by_document(
                    reranked_stream,
                    target_k=max(effective_top_k, 8),
                    max_per_doc=3,
                    min_docs=2,
                )
                # Intent-based affinity (Issue 2, Fix B)
                reranked_stream = _apply_intent_affinity(
                    reranked_stream, intent,
                    min_each=2, target_k=max(effective_top_k, 8),
                )

            stop_words = {"what", "is", "are", "the", "for", "with", "from", "this", "that",
                          "how", "to", "do", "does", "should", "can", "will"}
            query_words = [w.lower() for w in rewritten_query.split() if len(w) > 3 and w.lower() not in stop_words]
            all_keywords = list(set([kw.lower() for kw in enhanced_data.get("keywords", [])] + query_words))

            sources = []
            context_chunks = []
            for combined_score, result in reranked_stream[:effective_top_k]:
                payload = result.payload
                content = payload.get("content", "").strip()
                heading = payload.get("heading", "").strip()
                if not content or len(content) < 10:
                    continue
                sources.append({
                    "content": content,
                    "metadata": {
                        "chunk_id": payload.get("chunk_id"),
                        "doc_id": payload.get("doc_id"),
                        "source_file": payload.get("source_file"),
                        "type": payload.get("type"),
                        "heading": heading,
                        "language": payload.get("language", "")
                    },
                    "relevance_score": float(combined_score)
                })
                context_chunks.append(f"{heading}\n{content}" if heading else content)

            top_score = sources[0]["relevance_score"] if sources else 0.0
            confidence = _confidence_label(top_score)

            # Hard fallback
            if not context_chunks or top_score < FALLBACK_SCORE_THRESHOLD:
                log_query(
                    query_text=body.query,
                    chunks_retrieved=len(sources),
                    retrieval_score=top_score,
                    retrieval_latency_ms=retrieval_latency_ms,
                    response_latency_ms=int((time.time() - total_start) * 1000),
                    tokens_used=0,
                    source_cited=False,
                    fallback_triggered=True,
                    model_used="gemini",
                )
                add_turn(conversation_id, "assistant", FALLBACK_MESSAGE, sources_used=[])
                yield {"data": json.dumps({"token": FALLBACK_MESSAGE})}
                yield {"data": json.dumps({
                    "done": True, "sources": [], "context_used": [],
                    "confidence": "LOW", "fallback_triggered": True,
                    "conversation_id": conversation_id,
                    "used_context": used_context,
                    "prior_turn_count": len(prior_turns),
                })}
                return

            context = "\n\n---\n\n".join(context_chunks[:5])

            # Stream tokens — feed the rewritten query so the answer reflects
            # the resolved intent.
            full_answer = ""
            async for token in gemini_service.stream_answer(rewritten_query, context):
                full_answer += token
                yield {"data": json.dumps({"token": token})}
                await asyncio.sleep(0)

            response_latency_ms = int((time.time() - total_start) * 1000)
            logger.info("Stream complete in %.2fs", response_latency_ms / 1000)

            fallback_phrases = ["i don't know", "i don't have", "not found", "cannot find"]
            fallback_triggered = any(p in full_answer.lower() for p in fallback_phrases)

            tokens_used = 0  # Gemini token counting not tracked
            stream_qid = log_query(
                query_text=body.query,
                chunks_retrieved=len(sources),
                retrieval_score=top_score,
                retrieval_latency_ms=retrieval_latency_ms,
                response_latency_ms=response_latency_ms,
                tokens_used=tokens_used,
                source_cited=len(sources) > 0,
                fallback_triggered=fallback_triggered,
                model_used="gemini",
            )

            completed = QueryResponse(
                answer=full_answer, sources=sources, context_used=context_chunks,
                confidence=confidence, fallback_triggered=fallback_triggered,
                query_id=stream_qid,
            )
            query_cache.set(body.query, completed, body.doc_id)

            add_turn(conversation_id, "assistant", full_answer, sources_used=sources)

            yield {"data": json.dumps({
                "done": True,
                "sources": sources,
                "context_used": context_chunks,
                "confidence": confidence,
                "fallback_triggered": fallback_triggered,
                "query_id": stream_qid,
                "conversation_id": conversation_id,
                "used_context": used_context,
                "prior_turn_count": len(prior_turns),
            })}

        except Exception as e:
            logger.exception("Error in /chat/stream")
            yield {"data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@router.post("/new_conversation", status_code=status.HTTP_201_CREATED)
async def new_conversation():
    """Mint a fresh conversation_id for the client to thread subsequent queries on."""
    return {"conversation_id": create_conversation()}


@router.get("/conversation/{conversation_id}", status_code=status.HTTP_200_OK)
async def fetch_conversation(conversation_id: str):
    """Return all turns + metadata for a conversation."""
    convo = get_full_conversation(conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.delete("/conversation/{conversation_id}", status_code=status.HTTP_200_OK)
async def end_conversation(conversation_id: str):
    """Soft-delete a conversation. Turns stay in the table for analytics."""
    ok = soft_delete_conversation(conversation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "conversation_id": conversation_id}


@router.post("/feedback", status_code=status.HTTP_200_OK)
async def submit_feedback(body: FeedbackRequest):
    """Record thumbs-up (+1) or thumbs-down (-1) for a completed query."""
    if body.feedback not in (1, -1):
        raise HTTPException(status_code=400, detail="feedback must be 1 or -1")
    ok = record_feedback(body.query_id, body.feedback)
    if not ok:
        raise HTTPException(status_code=404, detail="Query ID not found or update failed")
    return {"ok": True}
