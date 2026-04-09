import logging
import os
import hashlib
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from qdrant_client.models import PointStruct

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client, ensure_collection_exists
from app.models.document import Document, Chunk as ChunkModel
from app.services.chunking import chunk_document
from app.services.processing import PDFProcessor, HTMLProcessor
from app.services.embeddings import embedding_service
from app.core.database import Base, engine

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'.pdf', '.md', '.txt', '.html', '.htm', '.rst', '.json', '.yaml', '.yml'}


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    total_chunks: int
    text_chunks: int
    code_chunks: int
    status: str


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    source_type: Optional[str] = None,
    db: Session = Depends(get_db)
) -> UploadResponse:
    """
    Upload a document (PDF, Markdown, TXT, HTML, etc.).
    Chunks it and stores embeddings in Qdrant.
    Max file size: 50 MB.
    """
    try:
        filename = file.filename or "unknown"
        file_ext = os.path.splitext(filename)[1].lower() if '.' in filename else ''

        # Validate extension
        if file_ext and file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # Read content with size check
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large ({len(content) // 1024 // 1024} MB). Maximum allowed is 50 MB."
            )

        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

        # Generate doc_id from content hash
        doc_id = hashlib.md5(content).hexdigest()

        # Deduplicate
        existing_doc = db.query(Document).filter(Document.id == doc_id).first()
        if existing_doc:
            logger.info("Document already exists: %s (%s)", filename, doc_id)
            return UploadResponse(
                doc_id=doc_id,
                filename=filename,
                total_chunks=existing_doc.total_chunks,
                text_chunks=existing_doc.text_chunks,
                code_chunks=existing_doc.code_chunks,
                status="already_exists"
            )

        # Process based on file type
        if file_ext == '.pdf':
            processor = PDFProcessor()
            chunks = processor.process_pdf(content, filename, doc_id)
        elif file_ext in ['.html', '.htm']:
            try:
                html_content = content.decode('utf-8')
            except UnicodeDecodeError:
                html_content = content.decode('utf-8', errors='ignore')
            processor = HTMLProcessor()
            chunks = processor.process_html(html_content, filename, doc_id)
        else:
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = content.decode('utf-8', errors='ignore')
            chunks = chunk_document(text_content, filename, doc_id)

        for chunk in chunks:
            chunk.doc_id = doc_id

        text_chunks = [c for c in chunks if c.type == "text"]
        code_chunks = [c for c in chunks if c.type == "code"]
        qdrant_client = get_qdrant_client()

        # Embed and store text chunks
        if text_chunks:
            text_contents = [c.content for c in text_chunks]
            text_embeddings = embedding_service.encode_text(text_contents)
            text_dim = embedding_service.get_text_embedding_dim()
            ensure_collection_exists("text_chunks", text_dim)
            points = [
                PointStruct(
                    id=chunk.chunk_id,
                    vector=embedding,
                    payload={
                        "chunk_id": chunk.chunk_id, "doc_id": chunk.doc_id,
                        "source_file": chunk.source_file, "start": chunk.start,
                        "end": chunk.end, "type": chunk.type,
                        "heading": chunk.heading or "", "content": chunk.content
                    }
                )
                for chunk, embedding in zip(text_chunks, text_embeddings)
            ]
            qdrant_client.upsert(collection_name="text_chunks", points=points)

        # Embed and store code chunks
        if code_chunks:
            code_contents = [c.content for c in code_chunks]
            code_embeddings = embedding_service.encode_code(code_contents)
            code_dim = embedding_service.get_code_embedding_dim()
            ensure_collection_exists("code_chunks", code_dim)
            points = [
                PointStruct(
                    id=chunk.chunk_id,
                    vector=embedding,
                    payload={
                        "chunk_id": chunk.chunk_id, "doc_id": chunk.doc_id,
                        "source_file": chunk.source_file, "start": chunk.start,
                        "end": chunk.end, "type": chunk.type,
                        "heading": chunk.heading or "", "language": chunk.language or "",
                        "content": chunk.content
                    }
                )
                for chunk, embedding in zip(code_chunks, code_embeddings)
            ]
            qdrant_client.upsert(collection_name="code_chunks", points=points)

        # Save metadata to PostgreSQL
        document = Document(
            id=doc_id, filename=filename, content_hash=doc_id,
            total_chunks=len(chunks), text_chunks=len(text_chunks), code_chunks=len(code_chunks)
        )
        db.add(document)
        for chunk in chunks:
            db.add(ChunkModel(
                id=chunk.chunk_id, doc_id=chunk.doc_id, source_file=chunk.source_file,
                content=chunk.content, start=chunk.start, end=chunk.end,
                chunk_type=chunk.type, heading=chunk.heading or "", language=chunk.language or ""
            ))
        db.commit()

        logger.info("Uploaded %s: %d text + %d code chunks (doc_id=%s)",
                    filename, len(text_chunks), len(code_chunks), doc_id)

        return UploadResponse(
            doc_id=doc_id, filename=filename, total_chunks=len(chunks),
            text_chunks=len(text_chunks), code_chunks=len(code_chunks), status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error processing upload: %s", filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )
