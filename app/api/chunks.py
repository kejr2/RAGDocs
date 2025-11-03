from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Dict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.models.document import Chunk

router = APIRouter()


class ChunkResponse(BaseModel):
    doc_id: str
    total_chunks: int
    chunks: List[Dict]


@router.get("/chunks/{doc_id}", status_code=status.HTTP_200_OK)
async def get_document_chunks(
    doc_id: str,
    db: Session = Depends(get_db)
) -> ChunkResponse:
    """
    Retrieve all chunks for a document for the viewer.
    """
    try:
        # Get Qdrant client
        qdrant_client = get_qdrant_client()
        
        # Build filter
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="doc_id",
                    match=MatchValue(value=doc_id)
                )
            ]
        )
        
        all_chunks = []
        
        # Get text chunks
        try:
            text_results = qdrant_client.scroll(
                collection_name="text_chunks",
                scroll_filter=query_filter,
                limit=10000
            )
            if text_results[0]:
                for point in text_results[0]:
                    all_chunks.append({
                        "content": point.payload.get("content", ""),
                        "metadata": {
                            "chunk_id": point.payload.get("chunk_id"),
                            "doc_id": point.payload.get("doc_id"),
                            "source_file": point.payload.get("source_file"),
                            "start": point.payload.get("start"),
                            "end": point.payload.get("end"),
                            "type": point.payload.get("type"),
                            "heading": point.payload.get("heading", ""),
                            "language": point.payload.get("language", "")
                        }
                    })
        except Exception:
            pass  # Collection might not exist yet
        
        # Get code chunks
        try:
            code_results = qdrant_client.scroll(
                collection_name="code_chunks",
                scroll_filter=query_filter,
                limit=10000
            )
            if code_results[0]:
                for point in code_results[0]:
                    all_chunks.append({
                        "content": point.payload.get("content", ""),
                        "metadata": {
                            "chunk_id": point.payload.get("chunk_id"),
                            "doc_id": point.payload.get("doc_id"),
                            "source_file": point.payload.get("source_file"),
                            "start": point.payload.get("start"),
                            "end": point.payload.get("end"),
                            "type": point.payload.get("type"),
                            "heading": point.payload.get("heading", ""),
                            "language": point.payload.get("language", "")
                        }
                    })
        except Exception:
            pass  # Collection might not exist yet
        
        # Sort by start position
        all_chunks.sort(key=lambda x: x['metadata']['start'])
        
        if not all_chunks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No chunks found for document {doc_id}"
            )
        
        return ChunkResponse(
            doc_id=doc_id,
            total_chunks=len(all_chunks),
            chunks=all_chunks
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving chunks: {str(e)}"
        )

