from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client, ensure_collection_exists
from app.services.embeddings import embedding_service
from app.services.gemini import gemini_service
from app.services.answer_formatter import format_basic_answer

router = APIRouter()


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


@router.post("/query", status_code=status.HTTP_200_OK)
async def query_chat(
    request: QueryRequest,
    db: Session = Depends(get_db)
) -> QueryResponse:
    """
    Query the RAG assistant using hybrid retrieval.
    Detects query type and searches appropriate collection.
    """
    try:
        query_type = detect_query_type(request.query)
        
        # Get Qdrant client
        qdrant_client = get_qdrant_client()
        
        # Build filter if doc_id is provided
        query_filter = None
        if request.doc_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=request.doc_id)
                    )
                ]
            )
        
        # Use hybrid search: search BOTH collections for better context
        # Especially important for questions like "What is X?"
        all_results = []
        
        # Search text chunks
        try:
            text_dim = embedding_service.get_text_embedding_dim()
            ensure_collection_exists("text_chunks", text_dim)
            text_embedding = embedding_service.encode_text([request.query])[0]
            text_results = qdrant_client.search(
                collection_name="text_chunks",
                query_vector=text_embedding,
                query_filter=query_filter,
                limit=request.top_k * 2  # Get more text results for better coverage
            )
            all_results.extend([(r, "text") for r in text_results])
        except Exception as e:
            print(f"Error searching text chunks: {e}")
        
        # Search code chunks (especially for "what is" questions that might have examples)
        # or if query type is code
        if query_type == "code" or any(word in request.query.lower() for word in ["what is", "what are", "explain", "describe", "define"]):
            try:
                code_dim = embedding_service.get_code_embedding_dim()
                ensure_collection_exists("code_chunks", code_dim)
                code_embedding = embedding_service.encode_code([request.query])[0]
                code_results = qdrant_client.search(
                    collection_name="code_chunks",
                    query_vector=code_embedding,
                    query_filter=query_filter,
                    limit=request.top_k
                )
                all_results.extend([(r, "code") for r in code_results])
            except Exception as e:
                print(f"Error searching code chunks: {e}")
        
        # Boost results with matching headings (especially for definition questions)
        query_lower = request.query.lower()
        is_definition_question = any(word in query_lower for word in ["what is", "what are", "define", "explain", "describe"])
        
        def boost_score(result_tuple):
            """Boost score if heading matches query keywords"""
            result, result_type = result_tuple
            score = result.score
            payload = result.payload
            heading = payload.get("heading", "").lower()
            
            # Boost if heading contains query keywords
            if is_definition_question:
                # Extract the main topic from query (e.g., "fastapi" from "what is fastapi?")
                topic = query_lower.replace("what is", "").replace("what are", "").replace("define", "").replace("explain", "").replace("describe", "").strip()
                topic = topic.replace("?", "").strip()
                
                # Strong boost for exact heading match like "## What is FastAPI?"
                if ("what is" in query_lower or "what are" in query_lower) and topic and topic in heading:
                    if "what is" in heading or "what are" in heading or "definition" in heading or "introduction" in heading:
                        score = score * 0.1  # Strong boost - prioritize definition sections
                
                # Medium boost for heading containing the topic
                elif topic and topic in heading:
                    score = score * 0.6
            
            return score
        
        # Sort all results by boosted score
        all_results.sort(key=boost_score)
        
        # Take top K results
        results = [r[0] for r in all_results[:request.top_k]]
        
        # Format results
        sources = []
        context_chunks = []
        
        for result in results:
            payload = result.payload
            distance = result.score
            content = payload.get("content", "")
            heading = payload.get("heading", "")
            
            sources.append({
                "content": content,
                "metadata": {
                    "chunk_id": payload.get("chunk_id"),
                    "doc_id": payload.get("doc_id"),
                    "source_file": payload.get("source_file"),
                    "start": payload.get("start"),
                    "end": payload.get("end"),
                    "type": payload.get("type"),
                    "heading": heading,
                    "language": payload.get("language", "")
                },
                "relevance_score": 1 - distance if distance > 0 else 1.0  # Convert distance to similarity
            })
            
            # Build context with heading information for better understanding
            if heading:
                context_chunks.append(f"{heading}\n{content}")
            else:
                context_chunks.append(content)
        
        # Build context for LLM with better formatting
        context = "\n\n---\n\n".join(context_chunks)
        
        # Generate answer with Gemini or fallback
        if gemini_service.enabled and context_chunks:
            answer = gemini_service.generate_answer(request.query, context)
            if not answer:
                # Fallback if Gemini fails
                answer = format_basic_answer(sources)
        else:
            # Fallback when Gemini is not enabled
            answer = format_basic_answer(sources)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            context_used=context_chunks
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying document: {str(e)}"
        )
