import logging
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client
from app.models.document import Document, Chunk

logger = logging.getLogger(__name__)
router = APIRouter()


class DeleteResponse(BaseModel):
    status: str
    doc_id: str


@router.delete("/documents/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db)
) -> DeleteResponse:
    """Delete a document and all its chunks from PostgreSQL and Qdrant."""
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found"
        )

    qdrant_client = get_qdrant_client()
    doc_filter = FilterSelector(
        filter=Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))])
    )

    for collection in ("text_chunks", "code_chunks"):
        try:
            qdrant_client.delete(collection_name=collection, points_selector=doc_filter)
            logger.info("Deleted vectors for doc %s from %s", doc_id, collection)
        except Exception as e:
            logger.warning("Could not delete from %s: %s", collection, e)

    try:
        db.query(Chunk).filter(Chunk.doc_id == doc_id).delete()
        db.delete(document)
        db.commit()
        logger.info("Deleted document %s from PostgreSQL", doc_id)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document metadata: {str(e)}"
        )

    return DeleteResponse(status="success", doc_id=doc_id)
