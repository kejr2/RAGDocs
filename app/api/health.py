import logging
import google.generativeai as genai
from fastapi import APIRouter, status, Depends
from pydantic import BaseModel
from datetime import datetime
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.qdrant_client import get_qdrant_client
from app.services.gemini import gemini_service
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    gemini_enabled: bool
    checks: Dict[str, str]


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Comprehensive health check: PostgreSQL, Qdrant, embedding models, Gemini API."""
    checks: Dict[str, str] = {}
    degraded = False

    # PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        logger.warning("Health check — PostgreSQL failed: %s", e)
        checks["postgres"] = f"error: {e}"
        degraded = True

    # Qdrant
    try:
        get_qdrant_client().get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        logger.warning("Health check — Qdrant failed: %s", e)
        checks["qdrant"] = f"error: {e}"
        degraded = True

    # Embedding models
    try:
        ready = embedding_service.models_ready
        checks["models"] = "ok" if ready else "loading"
        if not ready:
            degraded = True
    except Exception as e:
        checks["models"] = f"error: {e}"
        degraded = True

    # Gemini — probe with a cheap list_models call to verify API key validity
    if gemini_service.enabled:
        try:
            list(genai.list_models())
            checks["gemini"] = "ok"
        except Exception as e:
            logger.warning("Health check — Gemini API unreachable: %s", e)
            checks["gemini"] = f"api_error: {type(e).__name__}"
            degraded = True
    else:
        checks["gemini"] = "disabled"

    return HealthResponse(
        status="degraded" if degraded else "healthy",
        timestamp=datetime.now().isoformat(),
        gemini_enabled=gemini_service.enabled,
        checks=checks
    )


# ╔══════════════════════════════════════════════════╗
# ║  You found the easter egg! Built by Aditya K.   ║
# ╚══════════════════════════════════════════════════╝
@router.get("/_/whoami", include_in_schema=False)
async def whoami():
    return {
        "builder": "Aditya Kejriwal",
        "github": "github.com/kejr2",
        "message": "You found the easter egg 🥚 — nice curiosity!",
        "stack": ["FastAPI", "Qdrant", "Gemini", "React", "Sentence Transformers"],
    }
