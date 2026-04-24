import logging
import os
import mimetypes
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client
from app.models.document import Document, Chunk

logger = logging.getLogger(__name__)
router = APIRouter()

# Same directory as docs.py upload writes to — keep the env var name in sync.
UPLOAD_DIR = os.environ.get("RAGDOCS_UPLOAD_DIR", "/tmp/ragdocs_uploads")


def _find_stored_file(doc_id: str) -> Optional[str]:
    """Return path to the persisted original for *doc_id*, regardless of extension."""
    if not os.path.isdir(UPLOAD_DIR):
        return None
    for entry in os.listdir(UPLOAD_DIR):
        name, _ = os.path.splitext(entry)
        if name == doc_id:
            return os.path.join(UPLOAD_DIR, entry)
    return None


class DeleteResponse(BaseModel):
    status: str
    doc_id: str


class DocumentItem(BaseModel):
    doc_id: str
    filename: str
    total_chunks: int
    text_chunks: int
    code_chunks: int
    uploadedAt: Optional[str] = None


@router.get("/documents", status_code=status.HTTP_200_OK)
async def list_documents(db: Session = Depends(get_db)) -> List[DocumentItem]:
    """List every document indexed in PostgreSQL (newest first)."""
    rows = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        DocumentItem(
            doc_id=d.id,
            filename=d.filename,
            total_chunks=d.total_chunks or 0,
            text_chunks=d.text_chunks or 0,
            code_chunks=d.code_chunks or 0,
            uploadedAt=d.created_at.isoformat() if d.created_at else None,
        )
        for d in rows
    ]


@router.get("/file/{doc_id}", status_code=status.HTTP_200_OK)
async def get_document_file(doc_id: str, db: Session = Depends(get_db)):
    """
    Stream the original uploaded file for *doc_id*. Lets the frontend
    re-open any indexed document, not just ones uploaded in the current
    browser session.
    """
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    path = _find_stored_file(doc_id)
    if not path or not os.path.isfile(path):
        # Metadata exists, file does not — uploaded before persistence was on.
        raise HTTPException(
            status_code=410,
            detail=(
                "Original file is not available on the server "
                "(uploaded before file persistence was enabled). Re-upload to view."
            ),
        )

    media_type = (
        mimetypes.guess_type(document.filename)[0]
        or "application/octet-stream"
    )
    return FileResponse(path, media_type=media_type, filename=document.filename)


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

    # Remove persisted original file too.
    stored = _find_stored_file(doc_id)
    if stored:
        try:
            os.remove(stored)
        except Exception as e:
            logger.warning("Could not remove stored file %s: %s", stored, e)

    return DeleteResponse(status="success", doc_id=doc_id)
