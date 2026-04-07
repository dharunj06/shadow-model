from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models import Request, Prediction, ErrorLog, SeverityLevel
from app.core.logging import get_logger

logger = get_logger(__name__)


async def log_request(
    db: AsyncSession,
    request_id: UUID,
    input_data: dict,
    true_label=None,
    status: str = "success",
) -> Request:
    req = Request(
        id=request_id,
        input_data=input_data,
        true_label=true_label,
        status=status,
        created_at=datetime.utcnow(),
    )
    db.add(req)
    await db.flush()
    logger.info("request_logged", request_id=str(request_id))
    return req


async def log_prediction(
    db: AsyncSession,
    request_id: UUID,
    model_version: str,
    result: dict | None,
    latency_ms: float,
    is_error: bool,
) -> Prediction:
    prediction = None
    probability = None
    raw_output = None

    if result:
        prediction = result.get("prediction")
        probability = result.get("probability")
        raw_output = result

    pred = Prediction(
        request_id=request_id,
        model_version=model_version,
        prediction=prediction,
        probability=probability,
        raw_output=raw_output,
        latency_ms=latency_ms,
        is_error=is_error,
        created_at=datetime.utcnow(),
    )
    db.add(pred)
    await db.flush()
    return pred


async def log_error(
    db: AsyncSession,
    request_id: UUID | None,
    model_version: str | None,
    error_type: str,
    message: str,
    severity: SeverityLevel = SeverityLevel.ERROR,
    stack_trace: str | None = None,
) -> ErrorLog:
    err = ErrorLog(
        request_id=request_id,
        model_version=model_version,
        error_type=error_type,
        message=message,
        severity=severity,
        stack_trace=stack_trace,
        created_at=datetime.utcnow(),
    )
    db.add(err)
    await db.flush()
    logger.error(
        "error_logged",
        request_id=str(request_id) if request_id else None,
        model=model_version,
        type=error_type,
        severity=severity,
    )
    return err


async def get_recent_requests(db: AsyncSession, limit: int = 50, offset: int = 0):
    result = await db.execute(
        select(Request)
        .options(selectinload(Request.predictions))
        .options(selectinload(Request.errors))
        .order_by(Request.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_recent_errors(db: AsyncSession, limit: int = 50):
    result = await db.execute(
        select(ErrorLog)
        .order_by(ErrorLog.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
