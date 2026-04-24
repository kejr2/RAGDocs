from typing import Optional
from fastapi import APIRouter, status, HTTPException, Query
from app.services.metrics import get_metrics_summary, clear_query_logs

router = APIRouter()


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_metrics(exclude_before: Optional[str] = Query(None, description="ISO-8601 timestamp; drop queries older than this")):
    """Return aggregated metrics over the last 50 queries.

    Optional ?exclude_before=<iso_timestamp> pins the view to a time window
    (e.g. only today's queries) without wiping the table.
    """
    return get_metrics_summary(last_n=50, exclude_before=exclude_before)


@router.post("/admin/clear-query-logs", status_code=status.HTTP_200_OK)
async def clear_logs(confirm: Optional[str] = Query(None)):
    """Truncate the query_logs table. Requires ?confirm=yes.

    Intentionally not wired to a UI button — call via curl before recording
    a demo to reset the metrics view.
    """
    if confirm != "yes":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pass ?confirm=yes to truncate query_logs.",
        )
    deleted = clear_query_logs()
    return {"deleted": deleted}
