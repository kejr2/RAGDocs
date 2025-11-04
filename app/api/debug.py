"""
Debug endpoint for testing and inspecting LLM and embedding results
"""

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

router = APIRouter()


class DebugQueryRequest(BaseModel):
    query: str
    doc_id: Optional[str] = None
    top_k: int = 5


class DebugQueryResponse(BaseModel):
    # Query enhancement
    original_query: str
    enhanced_query: str
    keywords: List[str]
    query_type: str
    search_strategy: str
    
    # Embedding information
    text_embedding_dim: int
    code_embedding_dim: int
    embeddings_generated: bool
    
    # Retrieval results
    text_search_results: int
    code_search_results: int
    total_results_before_filtering: int
    filtered_results: int
    relevance_scores: List[float]
    
    # Retrieved chunks (detailed)
    chunks: List[Dict]
    
    # Context sent to LLM
    context_sent_to_llm: str
    context_chunk_count: int
    
    # LLM response
    llm_raw_response: Optional[str]
    llm_enabled: bool
    
    # Final answer
    final_answer: str


@router.post("/query", status_code=status.HTTP_200_OK)
async def debug_query(
    request: DebugQueryRequest,
    db: Session = Depends(get_db)
) -> DebugQueryResponse:
    """
    Debug endpoint to see exactly what the LLM receives and what embeddings are generated.
    Shows full retrieval pipeline with detailed information.
    """
    try:
        # Step 1: Query Enhancement
        print(f"\n{'='*60}")
        print(f"🔍 DEBUG: Original Query: {request.query}")
        print(f"{'='*60}\n")
        
        enhanced_data = query_enhancer.enhance_query(request.query)
        hybrid_search_query = query_enhancer.build_hybrid_search_query(enhanced_data, request.query)
        
        print(f"✨ Enhanced Query: {enhanced_data.get('enhanced_query', request.query)}")
        print(f"🔑 Keywords: {enhanced_data.get('keywords', [])}")
        print(f"📋 Query Type: {enhanced_data.get('query_type', 'general')}\n")
        
        # Step 2: Generate Embeddings
        print(f"{'='*60}")
        print(f"🧮 GENERATING EMBEDDINGS")
        print(f"{'='*60}\n")
        
        qdrant_client = get_qdrant_client()
        
        # Get embedding dimensions
        text_dim = embedding_service.get_text_embedding_dim()
        code_dim = embedding_service.get_code_embedding_dim()
        
        print(f"📐 Text embedding dimension: {text_dim}")
        print(f"📐 Code embedding dimension: {code_dim}\n")
        
        # Generate embeddings
        text_embedding = embedding_service.encode_text([hybrid_search_query])[0]
        code_embedding = embedding_service.encode_code([hybrid_search_query])[0]
        
        print(f"✅ Text embedding generated: {len(text_embedding)} dimensions")
        print(f"✅ Code embedding generated: {len(code_embedding)} dimensions\n")
        
        # Step 3: Vector Search
        print(f"{'='*60}")
        print(f"🔎 VECTOR SEARCH")
        print(f"{'='*60}\n")
        
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
            print(f"🎯 Filtering by doc_id: {request.doc_id}\n")
        
        all_results = []
        
        # Search text chunks
        text_results = []
        try:
            ensure_collection_exists("text_chunks", text_dim)
            search_limit = max(request.top_k * 3, 20)
            text_results = qdrant_client.search(
                collection_name="text_chunks",
                query_vector=text_embedding,
                query_filter=query_filter,
                limit=search_limit
            )
            all_results.extend([(r, "text") for r in text_results])
            print(f"📊 Text search returned: {len(text_results)} results")
            if text_results:
                print(f"   Best match distance: {text_results[0].score:.4f}")
        except Exception as e:
            print(f"❌ Error searching text chunks: {e}")
        
        # Search code chunks
        code_results = []
        should_search_code = enhanced_data.get("query_type") in ["example", "how-to"] or \
                            any(word in hybrid_search_query.lower() for word in ["what is", "code", "example"])
        
        if should_search_code:
            try:
                ensure_collection_exists("code_chunks", code_dim)
                code_limit = max(request.top_k * 2, 15)
                code_results = qdrant_client.search(
                    collection_name="code_chunks",
                    query_vector=code_embedding,
                    query_filter=query_filter,
                    limit=code_limit
                )
                all_results.extend([(r, "code") for r in code_results])
                print(f"📊 Code search returned: {len(code_results)} results")
                if code_results:
                    print(f"   Best match distance: {code_results[0].score:.4f}")
            except Exception as e:
                print(f"❌ Error searching code chunks: {e}")
        
        print(f"\n📊 Total results before filtering: {len(all_results)}\n")
        
        # Step 4: Filter and Process Results
        print(f"{'='*60}")
        print(f"🔍 FILTERING RESULTS")
        print(f"{'='*60}\n")
        
        MIN_RELEVANCE_THRESHOLD = 0.3
        MIN_CONTENT_LENGTH = 20
        
        # Sort by score (lower is better for distance)
        all_results.sort(key=lambda x: x[0].score)
        results = [r[0] for r in all_results[:request.top_k]]
        
        filtered_chunks = []
        relevance_scores = []
        
        for result in results:
            payload = result.payload
            distance = result.score
            content = payload.get("content", "").strip()
            heading = payload.get("heading", "").strip()
            
            # Skip empty or too short
            if not content or len(content) < MIN_CONTENT_LENGTH:
                continue
            
            # Calculate similarity
            similarity_score = 1 / (1 + distance) if distance >= 0 else 1.0
            
            # Filter by threshold
            if similarity_score < MIN_RELEVANCE_THRESHOLD:
                print(f"⚠️  Skipping chunk (relevance {similarity_score:.3f} < {MIN_RELEVANCE_THRESHOLD}): {content[:50]}...")
                continue
            
            relevance_scores.append(similarity_score)
            
            chunk_info = {
                "content": content,
                "metadata": {
                    "chunk_id": payload.get("chunk_id"),
                    "doc_id": payload.get("doc_id"),
                    "source_file": payload.get("source_file"),
                    "type": payload.get("type"),
                    "heading": heading,
                    "language": payload.get("language", "")
                },
                "relevance_score": similarity_score,
                "distance": distance
            }
            filtered_chunks.append(chunk_info)
            
            print(f"✅ Chunk accepted:")
            print(f"   Relevance: {similarity_score:.3f} (distance: {distance:.4f})")
            print(f"   Heading: {heading or 'No heading'}")
            print(f"   Content preview: {content[:100]}...")
            print()
        
        print(f"📊 After filtering: {len(filtered_chunks)} chunks passed relevance threshold\n")
        
        if not filtered_chunks:
            return DebugQueryResponse(
                original_query=request.query,
                enhanced_query=enhanced_data.get("enhanced_query", request.query),
                keywords=enhanced_data.get("keywords", []),
                query_type=enhanced_data.get("query_type", "general"),
                search_strategy=enhanced_data.get("search_strategy", "broad"),
                text_embedding_dim=text_dim,
                code_embedding_dim=code_dim,
                embeddings_generated=True,
                text_search_results=len(text_results),
                code_search_results=len(code_results),
                total_results_before_filtering=len(all_results),
                filtered_results=0,
                relevance_scores=[],
                chunks=[],
                context_sent_to_llm="",
                context_chunk_count=0,
                llm_raw_response=None,
                llm_enabled=gemini_service.enabled,
                final_answer="No relevant chunks found after filtering."
            )
        
        # Step 5: Build Context
        print(f"{'='*60}")
        print(f"📝 BUILDING CONTEXT FOR LLM")
        print(f"{'='*60}\n")
        
        context_chunks = []
        for chunk in filtered_chunks[:5]:  # Limit to top 5
            heading = chunk["metadata"]["heading"]
            content = chunk["content"]
            if heading:
                context_chunks.append(f"{heading}\n{content}")
            else:
                context_chunks.append(content)
        
        context = "\n\n---\n\n".join(context_chunks)
        
        print(f"📝 Context built with {len(context_chunks)} chunks")
        print(f"📏 Context length: {len(context)} characters\n")
        print("📄 Context preview:")
        print("-" * 60)
        print(context[:500] + "..." if len(context) > 500 else context)
        print("-" * 60)
        print()
        
        # Step 6: LLM Generation
        print(f"{'='*60}")
        print(f"🤖 LLM GENERATION")
        print(f"{'='*60}\n")
        
        llm_raw_response = None
        final_answer = ""
        
        if gemini_service.enabled and gemini_service.model:
            print(f"✅ Gemini is enabled")
            print(f"📤 Sending to LLM...\n")
            
            try:
                prompt = f"""You are an expert documentation assistant. Your task is to provide accurate, helpful answers based ONLY on the provided context.

CONTEXT FROM DOCUMENTATION:
{context}

USER QUESTION: {request.query}

IMPORTANT INSTRUCTIONS:
1. ANSWER STRICTLY BASED ON THE CONTEXT PROVIDED ABOVE. Do not use external knowledge.
2. If the context contains a direct answer, provide it clearly and concisely.
3. Include relevant code examples using proper markdown formatting (```language)
4. If the context doesn't contain enough information, clearly state: "Based on the provided context, I cannot find a complete answer to this question."

ANSWER (based on context only):"""
                
                response = gemini_service.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "top_p": 0.8,
                        "top_k": 40,
                        "max_output_tokens": 2048,
                    }
                )
                
                llm_raw_response = response.text if hasattr(response, 'text') else str(response)
                final_answer = llm_raw_response
                
                print(f"✅ LLM Response received ({len(llm_raw_response)} characters)")
                print("\n📄 LLM Response:")
                print("-" * 60)
                print(llm_raw_response[:1000] + "..." if len(llm_raw_response) > 1000 else llm_raw_response)
                print("-" * 60)
                print()
                
            except Exception as e:
                print(f"❌ LLM Error: {e}")
                final_answer = f"LLM Error: {str(e)}"
        else:
            print(f"⚠️  Gemini is not enabled")
            final_answer = "LLM is not enabled"
        
        print(f"{'='*60}")
        print(f"✅ DEBUG COMPLETE")
        print(f"{'='*60}\n")
        
        return DebugQueryResponse(
            original_query=request.query,
            enhanced_query=enhanced_data.get("enhanced_query", request.query),
            keywords=enhanced_data.get("keywords", []),
            query_type=enhanced_data.get("query_type", "general"),
            search_strategy=enhanced_data.get("search_strategy", "broad"),
            text_embedding_dim=text_dim,
            code_embedding_dim=code_dim,
            embeddings_generated=True,
            text_search_results=len(text_results),
            code_search_results=len(code_results),
            total_results_before_filtering=len(all_results),
            filtered_results=len(filtered_chunks),
            relevance_scores=relevance_scores,
            chunks=filtered_chunks,
            context_sent_to_llm=context,
            context_chunk_count=len(context_chunks),
            llm_raw_response=llm_raw_response,
            llm_enabled=gemini_service.enabled,
            final_answer=final_answer
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug query error: {str(e)}"
        )

