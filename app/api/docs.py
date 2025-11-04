from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from qdrant_client.models import PointStruct
import hashlib

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client, ensure_collection_exists
from app.models.document import Document, Chunk as ChunkModel
from app.services.chunking import chunk_document
from app.services.processing import PDFProcessor, HTMLProcessor
from app.services.embeddings import embedding_service
from app.core.database import Base, engine
import os

router = APIRouter()


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
    Upload a document (PDF, API docs, code files, etc.)
    Chunks it and stores in appropriate Qdrant collections.
    """
    try:
        # Read file content
        content = await file.read()
        filename = file.filename or "unknown"
        
        # Detect file type
        file_ext = os.path.splitext(filename)[1].lower() if '.' in filename else ''
        
        # Generate doc_id from content hash (use raw content for consistency)
        doc_id = hashlib.md5(content).hexdigest()
        
        # Check if document already exists
        existing_doc = db.query(Document).filter(Document.id == doc_id).first()
        if existing_doc:
            return UploadResponse(
                doc_id=doc_id,
                filename=filename,
                total_chunks=existing_doc.total_chunks,
                text_chunks=existing_doc.text_chunks,
                code_chunks=existing_doc.code_chunks,
                status="already_exists"
            )
        
        # Process document based on file type
        if file_ext == '.pdf':
            # Process PDF
            processor = PDFProcessor()
            chunks = processor.process_pdf(content, filename, doc_id)
        elif file_ext in ['.html', '.htm']:
            # Process HTML
            try:
                html_content = content.decode('utf-8')
            except:
                html_content = content.decode('utf-8', errors='ignore')
            processor = HTMLProcessor()
            chunks = processor.process_html(html_content, filename, doc_id)
        else:
            # Default: text processing
            try:
                text_content = content.decode('utf-8')
            except:
                text_content = content.decode('utf-8', errors='ignore')
            chunks = chunk_document(text_content, filename, doc_id)
        
        # Ensure all chunks have the correct doc_id
        for chunk in chunks:
            chunk.doc_id = doc_id
        
        # Separate text and code chunks
        text_chunks = [c for c in chunks if c.type == "text"]
        code_chunks = [c for c in chunks if c.type == "code"]
        
        # Get Qdrant client
        qdrant_client = get_qdrant_client()
        
        # Embed and store text chunks
        if text_chunks:
            text_contents = [c.content for c in text_chunks]
            text_embeddings = embedding_service.encode_text(text_contents)
            text_dim = embedding_service.get_text_embedding_dim()
            
            # Ensure text collection exists
            ensure_collection_exists("text_chunks", text_dim)
            
            # Create points for Qdrant
            points = []
            for chunk, embedding in zip(text_chunks, text_embeddings):
                points.append(PointStruct(
                    id=chunk.chunk_id,
                    vector=embedding,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "doc_id": chunk.doc_id,
                        "source_file": chunk.source_file,
                        "start": chunk.start,
                        "end": chunk.end,
                        "type": chunk.type,
                        "heading": chunk.heading or "",
                        "content": chunk.content
                    }
                ))
            
            # Insert into Qdrant
            qdrant_client.upsert(
                collection_name="text_chunks",
                points=points
            )
        
        # Embed and store code chunks
        if code_chunks:
            code_contents = [c.content for c in code_chunks]
            code_embeddings = embedding_service.encode_code(code_contents)
            code_dim = embedding_service.get_code_embedding_dim()
            
            # Ensure code collection exists
            ensure_collection_exists("code_chunks", code_dim)
            
            # Create points for Qdrant
            points = []
            for chunk, embedding in zip(code_chunks, code_embeddings):
                points.append(PointStruct(
                    id=chunk.chunk_id,
                    vector=embedding,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "doc_id": chunk.doc_id,
                        "source_file": chunk.source_file,
                        "start": chunk.start,
                        "end": chunk.end,
                        "type": chunk.type,
                        "heading": chunk.heading or "",
                        "language": chunk.language or "",
                        "content": chunk.content
                    }
                ))
            
            # Insert into Qdrant
            qdrant_client.upsert(
                collection_name="code_chunks",
                points=points
            )
        
        # Save document metadata to PostgreSQL
        document = Document(
            id=doc_id,
            filename=file.filename or "unknown",
            content_hash=doc_id,
            total_chunks=len(chunks),
            text_chunks=len(text_chunks),
            code_chunks=len(code_chunks)
        )
        db.add(document)
        
        # Save chunk metadata to PostgreSQL
        for chunk in chunks:
            chunk_model = ChunkModel(
                id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                source_file=chunk.source_file,
                content=chunk.content,
                start=chunk.start,
                end=chunk.end,
                chunk_type=chunk.type,
                heading=chunk.heading or "",
                language=chunk.language or ""
            )
            db.add(chunk_model)
        
        db.commit()
        
        return UploadResponse(
            doc_id=doc_id,
            filename=file.filename or "unknown",
            total_chunks=len(chunks),
            text_chunks=len(text_chunks),
            code_chunks=len(code_chunks),
            status="success"
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )
