"""
Test endpoints for directly querying vector database and inspecting results
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client, ensure_collection_exists
from app.services.embeddings import embedding_service

router = APIRouter()


class VectorSearchRequest(BaseModel):
    query: str
    collection: str = "text_chunks"  # "text_chunks" or "code_chunks"
    doc_id: Optional[str] = None
    top_k: int = 10
    min_score: Optional[float] = None  # Minimum similarity score


class VectorSearchResponse(BaseModel):
    query: str
    collection: str
    embedding_dim: int
    total_results: int
    results: List[Dict]
    query_embedding_sample: List[float]  # First 10 dimensions as sample


class CompareSearchRequest(BaseModel):
    query: str
    doc_id: Optional[str] = None
    top_k: int = 10


class CompareSearchResponse(BaseModel):
    query: str
    text_chunks: List[Dict]
    code_chunks: List[Dict]
    text_count: int
    code_count: int


@router.post("/search/text", status_code=status.HTTP_200_OK)
async def search_text_chunks(
    request: VectorSearchRequest,
    db: Session = Depends(get_db)
) -> VectorSearchResponse:
    """
    Direct semantic search in text_chunks collection.
    See raw vector search results.
    """
    try:
        print(f"\n{'='*60}")
        print(f"🔍 TEST: Searching TEXT chunks")
        print(f"Query: {request.query}")
        print(f"Doc ID: {request.doc_id or 'All documents'}")
        print(f"Top K: {request.top_k}")
        print(f"{'='*60}\n")
        
        qdrant_client = get_qdrant_client()
        
        # Generate text embedding
        text_dim = embedding_service.get_text_embedding_dim()
        ensure_collection_exists("text_chunks", text_dim)
        
        text_embedding = embedding_service.encode_text([request.query])[0]
        
        print(f"📐 Embedding dimension: {text_dim}")
        print(f"✅ Embedding generated: {len(text_embedding)} dimensions\n")
        
        # Build filter
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
        
        # Search
        search_results = qdrant_client.search(
            collection_name="text_chunks",
            query_vector=text_embedding,
            query_filter=query_filter,
            limit=request.top_k
        )
        
        print(f"📊 Search returned {len(search_results)} results\n")
        
        # Process results
        results = []
        for i, result in enumerate(search_results, 1):
            payload = result.payload
            distance = result.score
            similarity = 1 / (1 + distance) if distance >= 0 else 1.0
            
            # Apply minimum score filter if provided
            if request.min_score and similarity < request.min_score:
                continue
            
            content = payload.get("content", "").strip()
            heading = payload.get("heading", "").strip()
            
            chunk_info = {
                "rank": i,
                "distance": float(distance),
                "similarity_score": float(similarity),
                "content": content,
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "content_length": len(content),
                "metadata": {
                    "chunk_id": payload.get("chunk_id"),
                    "doc_id": payload.get("doc_id"),
                    "source_file": payload.get("source_file"),
                    "type": payload.get("type"),
                    "heading": heading,
                    "start": payload.get("start"),
                    "end": payload.get("end")
                }
            }
            
            results.append(chunk_info)
            
            print(f"Result {i}:")
            print(f"  Distance: {distance:.4f}")
            print(f"  Similarity: {similarity:.4f} ({similarity*100:.1f}%)")
            print(f"  Heading: {heading or 'No heading'}")
            print(f"  Content: {content[:150]}...")
            print()
        
        # Sample embedding (first 10 dimensions)
        embedding_sample = text_embedding[:10].tolist() if hasattr(text_embedding, 'tolist') else text_embedding[:10]
        
        return VectorSearchResponse(
            query=request.query,
            collection="text_chunks",
            embedding_dim=text_dim,
            total_results=len(results),
            results=results,
            query_embedding_sample=embedding_sample
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching text chunks: {str(e)}"
        )


@router.post("/search/code", status_code=status.HTTP_200_OK)
async def search_code_chunks(
    request: VectorSearchRequest,
    db: Session = Depends(get_db)
) -> VectorSearchResponse:
    """
    Direct semantic search in code_chunks collection.
    See raw vector search results.
    """
    try:
        print(f"\n{'='*60}")
        print(f"🔍 TEST: Searching CODE chunks")
        print(f"Query: {request.query}")
        print(f"Doc ID: {request.doc_id or 'All documents'}")
        print(f"Top K: {request.top_k}")
        print(f"{'='*60}\n")
        
        qdrant_client = get_qdrant_client()
        
        # Generate code embedding
        code_dim = embedding_service.get_code_embedding_dim()
        ensure_collection_exists("code_chunks", code_dim)
        
        code_embedding = embedding_service.encode_code([request.query])[0]
        
        print(f"📐 Embedding dimension: {code_dim}")
        print(f"✅ Embedding generated: {len(code_embedding)} dimensions\n")
        
        # Build filter
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
        
        # Search
        search_results = qdrant_client.search(
            collection_name="code_chunks",
            query_vector=code_embedding,
            query_filter=query_filter,
            limit=request.top_k
        )
        
        print(f"📊 Search returned {len(search_results)} results\n")
        
        # Process results
        results = []
        for i, result in enumerate(search_results, 1):
            payload = result.payload
            distance = result.score
            similarity = 1 / (1 + distance) if distance >= 0 else 1.0
            
            # Apply minimum score filter if provided
            if request.min_score and similarity < request.min_score:
                continue
            
            content = payload.get("content", "").strip()
            heading = payload.get("heading", "").strip()
            language = payload.get("language", "")
            
            chunk_info = {
                "rank": i,
                "distance": float(distance),
                "similarity_score": float(similarity),
                "content": content,
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "content_length": len(content),
                "metadata": {
                    "chunk_id": payload.get("chunk_id"),
                    "doc_id": payload.get("doc_id"),
                    "source_file": payload.get("source_file"),
                    "type": payload.get("type"),
                    "heading": heading,
                    "language": language,
                    "start": payload.get("start"),
                    "end": payload.get("end")
                }
            }
            
            results.append(chunk_info)
            
            print(f"Result {i}:")
            print(f"  Distance: {distance:.4f}")
            print(f"  Similarity: {similarity:.4f} ({similarity*100:.1f}%)")
            print(f"  Language: {language or 'unknown'}")
            print(f"  Heading: {heading or 'No heading'}")
            print(f"  Content: {content[:150]}...")
            print()
        
        # Sample embedding (first 10 dimensions)
        embedding_sample = code_embedding[:10].tolist() if hasattr(code_embedding, 'tolist') else code_embedding[:10]
        
        return VectorSearchResponse(
            query=request.query,
            collection="code_chunks",
            embedding_dim=code_dim,
            total_results=len(results),
            results=results,
            query_embedding_sample=embedding_sample
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching code chunks: {str(e)}"
        )


@router.post("/search/compare", status_code=status.HTTP_200_OK)
async def compare_text_code_search(
    request: CompareSearchRequest,
    db: Session = Depends(get_db)
) -> CompareSearchResponse:
    """
    Compare search results from both text and code collections side-by-side.
    See which collection returns better results for your query.
    """
    try:
        print(f"\n{'='*60}")
        print(f"🔍 TEST: Comparing TEXT vs CODE search")
        print(f"Query: {request.query}")
        print(f"{'='*60}\n")
        
        qdrant_client = get_qdrant_client()
        
        # Generate both embeddings
        text_dim = embedding_service.get_text_embedding_dim()
        code_dim = embedding_service.get_code_embedding_dim()
        
        text_embedding = embedding_service.encode_text([request.query])[0]
        code_embedding = embedding_service.encode_code([request.query])[0]
        
        # Build filter
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
        
        # Search both collections
        text_results = qdrant_client.search(
            collection_name="text_chunks",
            query_vector=text_embedding,
            query_filter=query_filter,
            limit=request.top_k
        )
        
        code_results = qdrant_client.search(
            collection_name="code_chunks",
            query_vector=code_embedding,
            query_filter=query_filter,
            limit=request.top_k
        )
        
        # Process text results
        text_chunks = []
        for i, result in enumerate(text_results, 1):
            payload = result.payload
            distance = result.score
            similarity = 1 / (1 + distance) if distance >= 0 else 1.0
            
            text_chunks.append({
                "rank": i,
                "distance": float(distance),
                "similarity_score": float(similarity),
                "content": payload.get("content", "").strip(),
                "content_preview": payload.get("content", "")[:200] + "..." if len(payload.get("content", "")) > 200 else payload.get("content", ""),
                "heading": payload.get("heading", ""),
                "metadata": {
                    "chunk_id": payload.get("chunk_id"),
                    "doc_id": payload.get("doc_id"),
                    "source_file": payload.get("source_file"),
                    "type": payload.get("type")
                }
            })
        
        # Process code results
        code_chunks = []
        for i, result in enumerate(code_results, 1):
            payload = result.payload
            distance = result.score
            similarity = 1 / (1 + distance) if distance >= 0 else 1.0
            
            code_chunks.append({
                "rank": i,
                "distance": float(distance),
                "similarity_score": float(similarity),
                "content": payload.get("content", "").strip(),
                "content_preview": payload.get("content", "")[:200] + "..." if len(payload.get("content", "")) > 200 else payload.get("content", ""),
                "heading": payload.get("heading", ""),
                "language": payload.get("language", ""),
                "metadata": {
                    "chunk_id": payload.get("chunk_id"),
                    "doc_id": payload.get("doc_id"),
                    "source_file": payload.get("source_file"),
                    "type": payload.get("type")
                }
            })
        
        print(f"📊 Text results: {len(text_chunks)}")
        print(f"📊 Code results: {len(code_chunks)}\n")
        
        if text_chunks:
            print(f"📝 Best text match: {text_chunks[0]['similarity_score']:.4f}")
        if code_chunks:
            print(f"💻 Best code match: {code_chunks[0]['similarity_score']:.4f}")
        
        return CompareSearchResponse(
            query=request.query,
            text_chunks=text_chunks,
            code_chunks=code_chunks,
            text_count=len(text_chunks),
            code_count=len(code_chunks)
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing search: {str(e)}"
        )


@router.get("/collections/info", status_code=status.HTTP_200_OK)
async def get_collections_info():
    """
    Get information about vector database collections.
    """
    try:
        qdrant_client = get_qdrant_client()
        
        collections_info = {}
        
        # Text chunks collection
        try:
            text_info = qdrant_client.get_collection("text_chunks")
            text_dim = embedding_service.get_text_embedding_dim()
            
            # Count points
            scroll_result = qdrant_client.scroll(
                collection_name="text_chunks",
                limit=10000
            )
            text_count = len(scroll_result[0]) if scroll_result[0] else 0
            
            collections_info["text_chunks"] = {
                "exists": True,
                "vector_size": text_dim,
                "points_count": text_count,
                "distance": text_info.config.params.vectors.size if hasattr(text_info.config.params, 'vectors') else text_dim
            }
        except Exception as e:
            collections_info["text_chunks"] = {
                "exists": False,
                "error": str(e)
            }
        
        # Code chunks collection
        try:
            code_info = qdrant_client.get_collection("code_chunks")
            code_dim = embedding_service.get_code_embedding_dim()
            
            # Count points
            scroll_result = qdrant_client.scroll(
                collection_name="code_chunks",
                limit=10000
            )
            code_count = len(scroll_result[0]) if scroll_result[0] else 0
            
            collections_info["code_chunks"] = {
                "exists": True,
                "vector_size": code_dim,
                "points_count": code_count,
                "distance": code_info.config.params.vectors.size if hasattr(code_info.config.params, 'vectors') else code_dim
            }
        except Exception as e:
            collections_info["code_chunks"] = {
                "exists": False,
                "error": str(e)
            }
        
        return collections_info
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting collections info: {str(e)}"
        )

