import logging
import json
import time
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from qdrant_client.models import Filter, FieldCondition, MatchValue
import asyncio
from concurrent.futures import ThreadPoolExecutor
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client, ensure_collection_exists
from app.services.embeddings import embedding_service
from app.services.gemini import gemini_service
from app.services.query_enhancer import query_enhancer
from app.services.answer_formatter import format_basic_answer
from app.services.retrieval import QueryCache

logger = logging.getLogger(__name__)

router = APIRouter()

# Thread pool for parallel CPU-bound operations
_executor = ThreadPoolExecutor(max_workers=4)

# Module-level query cache (shared across requests)
query_cache = QueryCache(max_size=500)


class QueryRequest(BaseModel):
    query: str
    doc_id: Optional[str] = None
    top_k: int = 10


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    context_used: List[str]


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

    # --- Cache check ---
    cached = query_cache.get(request.query, request.doc_id)
    if cached:
        logger.info("Cache hit for query: %s", request.query[:60])
        return cached

    # Step 1: Query enhancement
    t0 = time.time()
    logger.info("Processing query: %s", request.query[:80])
    enhanced_data = query_enhancer.enhance_query(request.query)
    logger.info("Query enhancement: %.2fs", time.time() - t0)

    required_topics = enhanced_data.get("required_topics", [])
    recommended_top_k = enhanced_data.get("recommended_top_k", request.top_k)
    multi_query_needed = enhanced_data.get("multi_query_needed", False)
    effective_top_k = max(request.top_k, recommended_top_k)

    hybrid_search_query = query_enhancer.build_hybrid_search_query(enhanced_data, request.query)
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
    t0 = time.time()
    if multi_query_needed and len(required_topics) > 1:
        logger.info("Multi-query mode: %d topics", len(required_topics))

        async def search_topic(topic: str):
            topic_query = f"{topic} {request.query}"
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
        text_limit = effective_top_k + 5
        code_limit = max(effective_top_k + 5, 15) if should_search_code else 0
        text_results, code_results = await search_collections_parallel(
            qdrant_client, text_embedding, code_embedding, text_dim, code_dim,
            query_filter, text_limit, code_limit, should_search_code
        )
        all_results.extend([(r, "text") for r in text_results])
        if should_search_code:
            all_results.extend([(r, "code") for r in code_results])

    logger.info("Retrieval: %.2fs, %d raw results", time.time() - t0, len(all_results))

    # Step 3: Scoring + filtering
    query_lower = hybrid_search_query.lower()
    query_keywords = enhanced_data.get("keywords", [])
    stop_words = {"what", "is", "are", "the", "for", "with", "from", "this", "that",
                  "how", "to", "do", "does", "should", "can", "will"}
    query_words = [w.lower() for w in request.query.split() if len(w) > 3 and w.lower() not in stop_words]
    all_keywords = list(set([kw.lower() for kw in query_keywords] + query_words))

    def score_result(result_tuple):
        result, _ = result_tuple
        score = result.score
        heading = result.payload.get("heading", "").lower()
        content_preview = result.payload.get("content", "").lower()[:200]
        heading_matches = sum(1 for kw in all_keywords if kw in heading)
        content_matches = sum(1 for kw in all_keywords if kw in content_preview)
        total = heading_matches + content_matches
        if heading_matches >= 2 or (heading_matches >= 1 and content_matches >= 2):
            score += 5.0
        elif heading_matches >= 1 or content_matches >= 2:
            score += 2.0
        elif total >= 1:
            score += 0.5
        return score

    all_results.sort(key=score_result, reverse=True)

    # Select top results
    results = [r[0] for r in all_results[:effective_top_k]]

    MIN_SCORE = 0.1
    MIN_CONTENT_LEN = 10
    sources = []
    context_chunks = []

    for result in results:
        payload = result.payload
        content = payload.get("content", "").strip()
        heading = payload.get("heading", "").strip()
        chunk_type = payload.get("type", "text")

        if not content or len(content) < MIN_CONTENT_LEN:
            continue
        if result.score < MIN_SCORE:
            keyword_matches = sum(1 for kw in all_keywords if kw in content.lower())
            if keyword_matches < 2:
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
                "language": payload.get("language", "")
            },
            "relevance_score": float(result.score)
        })
        context_chunks.append(f"{heading}\n{content}" if heading else content)

    if not context_chunks:
        logger.warning("No relevant chunks found for query: %s", request.query[:60])
        return QueryResponse(
            answer="I couldn't find relevant information to answer your question. "
                   "Try rephrasing or checking that the document covers this topic.",
            sources=[],
            context_used=[]
        )

    max_ctx = min(10 if (multi_query_needed and len(required_topics) > 1) else 5, len(context_chunks))
    context = "\n\n---\n\n".join(context_chunks[:max_ctx])
    logger.info("Using %d context chunks out of %d filtered results", max_ctx, len(sources))

    # Step 4: Answer generation
    t0 = time.time()
    if gemini_service.enabled:
        try:
            answer = gemini_service.generate_answer(request.query, context)
        except Exception as e:
            logger.error("Gemini failed after retries: %s", e)
            answer = None
        if not answer or len(answer.strip()) < 10:
            answer = format_basic_answer(sources)
    else:
        answer = format_basic_answer(sources)

    logger.info("Answer generation: %.2fs | Total: %.2fs", time.time() - t0, time.time() - total_start)

    response = QueryResponse(answer=answer, sources=sources, context_used=context_chunks)

    # Cache the result
    query_cache.set(request.query, response, request.doc_id)

    return response


@router.post("/query", status_code=status.HTTP_200_OK)
async def query_chat(
    request: QueryRequest,
    db: Session = Depends(get_db)
) -> QueryResponse:
    """Query the RAG assistant using hybrid retrieval with cross-encoder reranking."""
    try:
        return await _run_rag_pipeline(request)
    except Exception as e:
        logger.exception("Error in /chat/query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying document: {str(e)}"
        )


@router.post("/stream")
async def stream_chat(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """Stream answer tokens via Server-Sent Events (SSE).

    Events:
      - data: {"token": "..."} — partial answer token
      - data: {"done": true, "sources": [...], "context_used": [...]} — final event
      - data: {"error": "..."} — on failure
    """
    async def event_generator():
        try:
            total_start = time.time()

            # Run pipeline up to context building
            cached = query_cache.get(request.query, request.doc_id)
            if cached:
                logger.info("Stream cache hit: %s", request.query[:60])
                # Stream cached answer character by character for consistent UX
                chunk_size = 8
                answer = cached.answer
                for i in range(0, len(answer), chunk_size):
                    yield {"data": json.dumps({"token": answer[i:i+chunk_size]})}
                    await asyncio.sleep(0)
                yield {"data": json.dumps({
                    "done": True,
                    "sources": cached.sources,
                    "context_used": cached.context_used
                })}
                return

            enhanced_data = query_enhancer.enhance_query(request.query)
            hybrid_search_query = query_enhancer.build_hybrid_search_query(enhanced_data, request.query)
            query_type = detect_query_type(hybrid_search_query)

            qdrant_client = get_qdrant_client()
            query_filter = None
            if request.doc_id:
                query_filter = Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=request.doc_id))]
                )

            text_dim = embedding_service.get_text_embedding_dim()
            code_dim = embedding_service.get_code_embedding_dim()
            effective_top_k = max(request.top_k, enhanced_data.get("recommended_top_k", request.top_k))

            should_search_code = (
                query_type == "code" or
                enhanced_data.get("query_type") in ["example", "how-to", "multi-step"] or
                any(w in hybrid_search_query.lower() for w in
                    ["explain", "describe", "define", "example", "code"])
            )
            text_embedding, code_embedding = await generate_embeddings_parallel(hybrid_search_query)
            text_results, code_results = await search_collections_parallel(
                qdrant_client, text_embedding, code_embedding, text_dim, code_dim,
                query_filter, effective_top_k + 5,
                max(effective_top_k + 5, 15) if should_search_code else 0,
                should_search_code
            )

            all_results = [(r, "text") for r in text_results]
            if should_search_code:
                all_results.extend([(r, "code") for r in code_results])

            all_results.sort(key=lambda x: x[0].score, reverse=True)
            results = [r[0] for r in all_results[:effective_top_k]]

            stop_words = {"what", "is", "are", "the", "for", "with", "from", "this", "that",
                          "how", "to", "do", "does", "should", "can", "will"}
            query_words = [w.lower() for w in request.query.split() if len(w) > 3 and w.lower() not in stop_words]
            all_keywords = list(set([kw.lower() for kw in enhanced_data.get("keywords", [])] + query_words))

            sources = []
            context_chunks = []
            for result in results:
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
                    "relevance_score": float(result.score)
                })
                context_chunks.append(f"{heading}\n{content}" if heading else content)

            if not context_chunks:
                yield {"data": json.dumps({"token": "I couldn't find relevant information. Try rephrasing your question."})}
                yield {"data": json.dumps({"done": True, "sources": [], "context_used": []})}
                return

            context = "\n\n---\n\n".join(context_chunks[:5])

            # Stream tokens
            full_answer = ""
            async for token in gemini_service.stream_answer(request.query, context):
                full_answer += token
                yield {"data": json.dumps({"token": token})}
                await asyncio.sleep(0)

            logger.info("Stream complete in %.2fs", time.time() - total_start)

            # Cache completed response
            completed = QueryResponse(answer=full_answer, sources=sources, context_used=context_chunks)
            query_cache.set(request.query, completed, request.doc_id)

            yield {"data": json.dumps({"done": True, "sources": sources, "context_used": context_chunks})}

        except Exception as e:
            logger.exception("Error in /chat/stream")
            yield {"data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())
