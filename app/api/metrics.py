from fastapi import APIRouter, status
from app.services.metrics import get_metrics_summary

router = APIRouter()


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_metrics():
    """Return aggregated metrics over the last 50 queries."""
    return get_metrics_summary(last_n=50)
