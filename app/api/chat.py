from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client, ensure_collection_exists
from app.services.embeddings import embedding_service
from app.services.gemini import gemini_service
from app.services.query_enhancer import query_enhancer
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
        # Step 1: Enhance query using LLM for better retrieval
        print(f"🔍 Original query: {request.query}")
        enhanced_data = query_enhancer.enhance_query(request.query)
        
        # Get retrieval strategy from enhancement
        required_topics = enhanced_data.get("required_topics", [])
        recommended_top_k = enhanced_data.get("recommended_top_k", request.top_k)
        multi_query_needed = enhanced_data.get("multi_query_needed", False)
        
        # Use recommended top_k if higher than requested
        effective_top_k = max(request.top_k, recommended_top_k)
        
        print(f"✨ Enhanced query: {enhanced_data.get('enhanced_query', request.query)}")
        print(f"🔑 Keywords: {enhanced_data.get('keywords', [])}")
        print(f"📋 Query type: {enhanced_data.get('query_type', 'general')}")
        print(f"📚 Required topics: {required_topics}")
        print(f"🔢 Recommended top_k: {recommended_top_k} (using {effective_top_k})")
        print(f"🔄 Multi-query needed: {multi_query_needed}")
        
        # Build hybrid query for later use
        hybrid_search_query = query_enhancer.build_hybrid_search_query(enhanced_data, request.query)
        query_type = detect_query_type(hybrid_search_query)
        
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
        
        # If multi-query needed, search for each topic separately
        if multi_query_needed and len(required_topics) > 1:
            print(f"🔍 Multi-query mode: Searching for {len(required_topics)} topics")
            
            # Build hybrid query for main search
            hybrid_search_query = query_enhancer.build_hybrid_search_query(enhanced_data, request.query)
            
            # Search for each topic
            for topic in required_topics:
                print(f"  🔎 Searching for topic: {topic}")
                topic_query = f"{topic} {request.query}"
                
                # Search text chunks for this topic
                try:
                    text_dim = embedding_service.get_text_embedding_dim()
                    ensure_collection_exists("text_chunks", text_dim)
                    text_embedding = embedding_service.encode_text([topic_query])[0]
                    text_results = qdrant_client.search(
                        collection_name="text_chunks",
                        query_vector=text_embedding,
                        query_filter=query_filter,
                        limit=effective_top_k // len(required_topics) + 2  # Distribute chunks across topics
                    )
                    all_results.extend([(r, "text") for r in text_results])
                    print(f"    ✅ Found {len(text_results)} text chunks for {topic}")
                except Exception as e:
                    print(f"    ❌ Error searching text chunks for {topic}: {e}")
                
                # Search code chunks for this topic
                try:
                    code_dim = embedding_service.get_code_embedding_dim()
                    ensure_collection_exists("code_chunks", code_dim)
                    code_embedding = embedding_service.encode_code([topic_query])[0]
                    code_results = qdrant_client.search(
                        collection_name="code_chunks",
                        query_vector=code_embedding,
                        query_filter=query_filter,
                        limit=effective_top_k // len(required_topics) + 2
                    )
                    all_results.extend([(r, "code") for r in code_results])
                    print(f"    ✅ Found {len(code_results)} code chunks for {topic}")
                except Exception as e:
                    print(f"    ❌ Error searching code chunks for {topic}: {e}")
        else:
            # Single query mode (original behavior)
            hybrid_search_query = query_enhancer.build_hybrid_search_query(enhanced_data, request.query)
            
            # Search text chunks (use enhanced query)
            try:
                text_dim = embedding_service.get_text_embedding_dim()
                ensure_collection_exists("text_chunks", text_dim)
                text_embedding = embedding_service.encode_text([hybrid_search_query])[0]
                text_results = qdrant_client.search(
                    collection_name="text_chunks",
                    query_vector=text_embedding,
                    query_filter=query_filter,
                    limit=effective_top_k * 2  # Get more text results for better coverage
                )
                all_results.extend([(r, "text") for r in text_results])
            except Exception as e:
                print(f"Error searching text chunks: {e}")
            
            # Search code chunks (especially for "what is" questions that might have examples)
            # or if query type is code
            should_search_code = (
                query_type == "code" or 
                enhanced_data.get("query_type") in ["example", "how-to", "multi-step"] or
                any(word in hybrid_search_query.lower() for word in ["what is", "what are", "explain", "describe", "define", "example", "code"])
            )
            
            if should_search_code:
                try:
                    code_dim = embedding_service.get_code_embedding_dim()
                    ensure_collection_exists("code_chunks", code_dim)
                    code_embedding = embedding_service.encode_code([hybrid_search_query])[0]
                    
                    code_limit = max(effective_top_k * 2, 15)  # At least 15, or 2x top_k
                    
                    code_results = qdrant_client.search(
                        collection_name="code_chunks",
                        query_vector=code_embedding,
                        query_filter=query_filter,
                        limit=code_limit
                    )
                    
                    print(f"📊 Code search returned {len(code_results)} results")
                    all_results.extend([(r, "code") for r in code_results])
                except Exception as e:
                    print(f"❌ Error searching code chunks: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Boost results with matching headings (especially for definition questions)
        # Use enhanced data to better identify definition questions
        query_lower = hybrid_search_query.lower()
        is_definition_question = (
            enhanced_data.get("query_type") == "definition" or
            any(word in query_lower for word in ["what is", "what are", "define", "explain", "describe"]) or
            any(keyword in query_lower for keyword in enhanced_data.get("keywords", []))
        )
        
        def boost_score(result_tuple):
            """Boost score if heading matches query keywords"""
            result, result_type = result_tuple
            score = result.score
            payload = result.payload
            heading = payload.get("heading", "").lower()
            content = payload.get("content", "").lower()
            
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
            
            # Boost for test-related queries
            if any(word in query_lower for word in ["test", "testing", "test card", "card number"]):
                if "test" in heading or "test" in content[:100]:  # Check first 100 chars for performance
                    # Strong boost for test card numbers queries
                    if "card" in query_lower and ("card" in heading or "card" in content[:100]):
                        score = score * 0.2  # Strong boost for test card queries
                    else:
                        score = score * 0.5  # Medium boost for test-related queries
            
            return score
        
        # Sort all results by boosted score (lower is better for distance)
        all_results.sort(key=boost_score)
        
        # For multi-step/code queries, prioritize code chunks and ensure diversity
        if enhanced_data.get("query_type") in ["multi-step", "how-to", "example"] or "code" in hybrid_search_query.lower():
            # Separate code and text results
            code_results = [(r, t) for r, t in all_results if r.payload.get("type") == "code"]
            text_results = [(r, t) for r, t in all_results if r.payload.get("type") != "code"]
            
            # For multi-step queries, ensure we get code chunks covering all topics
            if multi_query_needed and len(required_topics) > 1:
                # Detect requested language from query
                query_lower = request.query.lower()
                requested_language = None
                if "node.js" in query_lower or "nodejs" in query_lower or "javascript" in query_lower:
                    requested_language = "javascript"
                elif "python" in query_lower:
                    requested_language = "python"
                
                # Prioritize code chunks that match the required topics AND language
                prioritized_code = []
                for topic in required_topics:
                    topic_lower = topic.lower()
                    matching_code = [(r, t) for r, t in code_results 
                                     if (topic_lower in r.payload.get("content", "").lower()[:200] or 
                                         topic_lower in r.payload.get("heading", "").lower()) and
                                        (not requested_language or 
                                         r.payload.get("language", "").lower() == requested_language.lower())]
                    prioritized_code.extend(matching_code[:3])  # Top 3 per topic
                
                # If language-specific code not found, include all matching topic code
                if not prioritized_code:
                    for topic in required_topics:
                        topic_lower = topic.lower()
                        matching_code = [(r, t) for r, t in code_results 
                                         if topic_lower in r.payload.get("content", "").lower()[:200] or 
                                            topic_lower in r.payload.get("heading", "").lower()]
                        prioritized_code.extend(matching_code[:3])
                
                # Add remaining code chunks (preferring requested language)
                remaining_code = [(r, t) for r, t in code_results 
                                  if (r, t) not in prioritized_code]
                if requested_language:
                    language_code = [(r, t) for r, t in remaining_code 
                                    if r.payload.get("language", "").lower() == requested_language.lower()]
                    other_code = [(r, t) for r, t in remaining_code 
                                 if r.payload.get("language", "").lower() != requested_language.lower()]
                    remaining_code = language_code + other_code
                
                code_results_sorted = prioritized_code + remaining_code
                
                # Take more code chunks for multi-step queries
                code_count = min(effective_top_k, len(code_results_sorted))
                text_count = min(effective_top_k - code_count, len(text_results))
                
                results = [r[0] for r in code_results_sorted[:code_count] + text_results[:text_count]]
                
                print(f"📊 Multi-step query: Prioritized {len(prioritized_code)} code chunks covering {len(required_topics)} topics (language: {requested_language or 'any'})")
            else:
                # For single-topic code queries, prioritize code chunks
                code_count = min(effective_top_k // 2 + 2, len(code_results))
                text_count = effective_top_k - code_count
                results = [r[0] for r in code_results[:code_count] + text_results[:text_count]]
        
        # Prioritize code chunks for installation/example queries
        # Boost code chunks to the top for queries about installation, examples, or "how to"
        elif enhanced_data.get("query_type") in ["how-to", "example"] or "install" in hybrid_search_query.lower():
            # Separate code and text results
            code_results = [(r, t) for r, t in all_results if r.payload.get("type") == "code"]
            text_results = [(r, t) for r, t in all_results if r.payload.get("type") != "code"]
            
            # For installation queries, prioritize chunks with "install" in content
            # Sort code results to put install commands first
            install_code = [(r, t) for r, t in code_results if "install" in r.payload.get("content", "").lower()]
            other_code = [(r, t) for r, t in code_results if "install" not in r.payload.get("content", "").lower()]
            code_results_sorted = install_code + other_code
            
            # Prioritize code chunks: take more code chunks for installation queries
            code_count = min(request.top_k // 2 + 2, len(code_results_sorted))  # Take more from code
            text_count = request.top_k - code_count
            
            # Combine: install code first, then other code, then text
            prioritized_results = code_results_sorted[:code_count] + text_results[:text_count]
            results = [r[0] for r in prioritized_results]
            
            print(f"📊 Prioritized code chunks: {len(install_code)} install commands + {code_count - len(install_code)} other code + {text_count} text")
        else:
            # Take top K results normally
            results = [r[0] for r in all_results[:request.top_k]]
        
        # Filter results by relevance threshold and minimum content length
        # Only use chunks that are actually relevant (distance < 0.7 = similarity > 0.3)
        # Lower threshold for code chunks since code similarity scores can be different
        MIN_RELEVANCE_THRESHOLD = 0.25  # Minimum similarity score (lowered to include code chunks)
        MIN_CONTENT_LENGTH = 10  # Minimum characters in content (lowered for short code commands)
        
        filtered_results = []
        sources = []
        context_chunks = []
        
        for result in results:
            payload = result.payload
            distance = result.score
            content = payload.get("content", "").strip()
            heading = payload.get("heading", "").strip()
            chunk_type = payload.get("type", "text")
            
            # Skip empty or too short content
            if not content or len(content) < MIN_CONTENT_LENGTH:
                continue
            
            # Convert distance to similarity score (lower distance = higher similarity)
            # Cosine distance ranges from 0 to 2, so similarity = 1 - (distance / 2)
            # For better threshold, use: similarity = 1 / (1 + distance)
            similarity_score = 1 / (1 + distance) if distance >= 0 else 1.0
            
            # Lower threshold for code chunks (they can have different similarity scores)
            # Code chunks with install commands might have lower scores but are still relevant
            threshold = MIN_RELEVANCE_THRESHOLD * 0.8 if chunk_type == "code" else MIN_RELEVANCE_THRESHOLD
            
            # Filter by relevance threshold
            if similarity_score < threshold:
                # For installation queries, be more lenient with code chunks
                if "install" in request.query.lower() and chunk_type == "code" and "install" in content.lower():
                    # Allow code chunks with install commands even if slightly below threshold
                    if similarity_score >= threshold * 0.7:
                        print(f"✅ Including install code chunk despite lower score: {similarity_score:.3f}")
                    else:
                        continue
                else:
                    continue
            
            # Add to sources
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
                "relevance_score": similarity_score
            })
            
            # Build context with heading information for better understanding
            if heading:
                context_chunks.append(f"{heading}\n{content}")
            else:
                context_chunks.append(content)
            
            filtered_results.append(result)
        
        # If no relevant results found, try with lower threshold or return empty
        if not context_chunks:
            print(f"⚠️  No relevant chunks found (threshold: {MIN_RELEVANCE_THRESHOLD})")
            print(f"   Total results: {len(results)}, All results: {len(all_results)}")
            # Return a helpful message instead of empty answer
            return QueryResponse(
                answer="I couldn't find relevant information to answer your question. Try:\n- Rephrasing your question\n- Using more specific keywords\n- Checking if the document contains information about this topic",
                sources=[],
                context_used=[]
            )
        
        # Build context for LLM with better formatting
        # For multi-topic queries, include more chunks to cover all topics
        if multi_query_needed and len(required_topics) > 1:
            # Include more chunks for multi-topic queries (up to 10 or all if less)
            max_context_chunks = min(10, len(context_chunks))
        else:
            # Limit context size to avoid token limits (keep top 5 most relevant)
            max_context_chunks = min(5, len(context_chunks))
        
        context_chunks_for_llm = context_chunks[:max_context_chunks]
        context = "\n\n---\n\n".join(context_chunks_for_llm)
        
        print(f"📊 Retrieved {len(filtered_results)} relevant chunks (from {len(results)} results)")
        print(f"📝 Using {len(context_chunks_for_llm)} chunks for context")
        
        # Generate answer with Gemini or fallback
        if gemini_service.enabled and context_chunks:
            answer = gemini_service.generate_answer(request.query, context)
            if not answer or len(answer.strip()) < 10:
                # Fallback if Gemini fails or returns empty
                print("⚠️  Gemini returned empty answer, using fallback")
                answer = format_basic_answer(sources)
        else:
            # Fallback when Gemini is not enabled
            answer = format_basic_answer(sources)
        
        # Ensure we have a valid answer
        if not answer or len(answer.strip()) < 5:
            answer = "I couldn't generate a reliable answer. Please try rephrasing your question or check if the document contains relevant information."
        
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
