from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, docs, chat, chunks, documents
from app.core.config import settings
from app.core.database import init_db, Base, engine
from app.core.qdrant_client import init_qdrant

app = FastAPI(
    title="RAGDocs API",
    description="RAG system for documentation and code with enhanced code retrieval",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(docs.router, prefix="/docs", tags=["docs"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(chunks.router, prefix="/docs", tags=["docs"])
app.include_router(documents.router, prefix="/docs", tags=["docs"])


@app.on_event("startup")
async def startup_event():
    """Initialize database and vector store connections on startup"""
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    await init_db()
    await init_qdrant()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    pass

