from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Document(Base):
    """Document model for storing document metadata"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)  # doc_id (MD5 hash)
    filename = Column(String, nullable=False)
    content_hash = Column(String, nullable=False)
    total_chunks = Column(Integer, default=0)
    text_chunks = Column(Integer, default=0)
    code_chunks = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Chunk(Base):
    """Chunk model for storing chunk metadata"""
    __tablename__ = "chunks"
    
    id = Column(String, primary_key=True)  # chunk_id
    doc_id = Column(String, nullable=False, index=True)
    source_file = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    start = Column(Integer, nullable=False)
    end = Column(Integer, nullable=False)
    chunk_type = Column(String, nullable=False)  # "text" or "code"
    heading = Column(String, nullable=True)
    language = Column(String, nullable=True)
    # enriched metadata (Fix 3)
    page_number = Column(Integer, nullable=True, default=0)
    section_heading = Column(Text, nullable=True, default="")
    has_table = Column(Boolean, nullable=True, default=False)
    has_list = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

