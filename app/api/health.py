from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime
from app.services.gemini import gemini_service

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    gemini_enabled: bool


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """
    Health check endpoint
    
    Returns:
        HealthResponse: Status of the API with timestamp and Gemini status
    """
    return HealthResponse(
        status="healthy", 
        timestamp=datetime.now().isoformat(),
        gemini_enabled=gemini_service.enabled
    )

