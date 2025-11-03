from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client
from app.models.document import Document, Chunk

router = APIRouter()


class DeleteResponse(BaseModel):
    status: str
    doc_id: str


@router.delete("/documents/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db)
) -> DeleteResponse:
    """Delete a document and all its chunks."""
    try:
        # Check if document exists
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {doc_id} not found"
            )
        
        # Get Qdrant client
        qdrant_client = get_qdrant_client()
        
        # Delete from Qdrant text collection
        try:
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
            # Get all point IDs matching the filter
            scroll_result = qdrant_client.scroll(
                collection_name="text_chunks",
                scroll_filter=filter_condition,
                limit=10000
            )
            if scroll_result[0]:  # If there are points
                point_ids = [point.id for point in scroll_result[0]]
                qdrant_client.delete(
                    collection_name="text_chunks",
                    points_selector=point_ids
                )
        except Exception as e:
            print(f"Warning: Could not delete from text_chunks: {e}")
        
        # Delete from Qdrant code collection
        try:
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
            # Get all point IDs matching the filter
            scroll_result = qdrant_client.scroll(
                collection_name="code_chunks",
                scroll_filter=filter_condition,
                limit=10000
            )
            if scroll_result[0]:  # If there are points
                point_ids = [point.id for point in scroll_result[0]]
                qdrant_client.delete(
                    collection_name="code_chunks",
                    points_selector=point_ids
                )
        except Exception as e:
            print(f"Warning: Could not delete from code_chunks: {e}")
        
        # Delete chunks from PostgreSQL
        db.query(Chunk).filter(Chunk.doc_id == doc_id).delete()
        
        # Delete document from PostgreSQL
        db.delete(document)
        db.commit()
        
        return DeleteResponse(
            status="success",
            doc_id=doc_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )

