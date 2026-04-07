from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.schemas import RequestSchema, ErrorLogSchema
from app.services.log_service import get_recent_requests, get_recent_errors
from app.core.logging import get_logger

router = APIRouter(prefix="/api/v1", tags=["Logs"])
logger = get_logger(__name__)


@router.get("/requests", response_model=list[RequestSchema])
async def list_requests(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of recent ingested requests with predictions."""
    records = await get_recent_requests(db, limit=limit, offset=offset)
    return records


@router.get("/errors", response_model=list[ErrorLogSchema])
async def list_errors(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return recent error logs across all models."""
    records = await get_recent_errors(db, limit=limit)
    return records
