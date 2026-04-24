import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import health, docs, chat, chunks, documents, debug, test_vectordb, metrics
from app.api.chat import limiter
from app.core.config import settings
from app.core.database import init_db, Base, engine
from app.core.qdrant_client import init_qdrant
from app.services.metrics import init_metrics_db
from app.services.conversations import init_conversations_db

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAGDocs API",
    description="Production-grade RAG system for code documentation",
    version="2.0.0"
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restrict to known origins; configure CORS_ORIGINS env var in production
cors_origins = settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log each request with method, path, status, and duration."""
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    logger.info(
        "%s %s %d %dms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms
    )
    return response


# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(docs.router, prefix="/docs", tags=["docs"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(chunks.router, prefix="/docs", tags=["docs"])
app.include_router(documents.router, prefix="/docs", tags=["docs"])
app.include_router(debug.router, prefix="/debug", tags=["debug"])
app.include_router(test_vectordb.router, prefix="/test/vectordb", tags=["test"])
app.include_router(metrics.router, tags=["metrics"])


def _migrate_chunks_schema():
    """
    Idempotently add the enriched-metadata columns (Fix 3) to an existing
    *chunks* table.  PostgreSQL 9.6+ supports ADD COLUMN IF NOT EXISTS so this
    is safe to run on every startup.
    """
    from sqlalchemy import text
    migrations = [
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page_number INTEGER DEFAULT 0",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS section_heading TEXT DEFAULT ''",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS has_table BOOLEAN DEFAULT FALSE",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS has_list BOOLEAN DEFAULT FALSE",
    ]
    try:
        with engine.connect() as conn:
            for sql in migrations:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as col_err:
                    conn.rollback()
                    logger.debug("Schema migration skipped: %s", col_err)
        logger.info("chunks schema migration complete")
    except Exception as e:
        logger.warning("Could not run chunks schema migration: %s", e)


@app.on_event("startup")
async def startup_event():
    """Initialize database and vector store connections on startup."""
    logger.info("Starting RAGDocs API...")
    Base.metadata.create_all(bind=engine)
    await init_db()
    await init_qdrant()
    init_metrics_db()
    init_conversations_db()
    _migrate_chunks_schema()
    logger.info("RAGDocs API ready")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("RAGDocs API shutting down")
