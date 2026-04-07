import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, AsyncSessionLocal
from app.api.schemas import IngestRequest, IngestResponse
from app.services.shadow_router import shadow_dispatch
from app.services.log_service import log_request, log_prediction, log_error
from app.db.models import SeverityLevel
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.core.logging import get_logger
from datetime import datetime
import time

router = APIRouter(prefix="/api/v1", tags=["Ingest"])
logger = get_logger(__name__)


async def _persist_shadow_result(
    request_id: uuid.UUID,
    features: list,
    true_label,
    shadow_result: dict,
):
    """Background task: persist predictions and any errors."""
    async with AsyncSessionLocal() as db:
        await log_request(db, request_id, {"features": features}, true_label)

        for version in ("v1", "v2"):
            data = shadow_result[version]
            await log_prediction(
                db,
                request_id=request_id,
                model_version=version,
                result=data["result"],
                latency_ms=data["latency_ms"],
                is_error=data["is_error"],
            )
            if data["is_error"]:
                error_type = data["error"] or "UnknownError"
                severity = SeverityLevel.WARNING if "timeout" in error_type.lower() else SeverityLevel.ERROR
                await log_error(
                    db,
                    request_id=request_id,
                    model_version=version,
                    error_type=error_type,
                    message=f"Model {version} failed: {data['error']}",
                    severity=severity,
                )

        await db.commit()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    payload: IngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts input features and fans out to both models in shadow mode.
    Returns only metadata — no model predictions are exposed.
    """
    request_id = uuid.uuid4()
    start = time.perf_counter()

    try:
        shadow_result = await shadow_dispatch(payload.features)
        REQUEST_COUNT.labels(status="success").inc()
    except Exception as e:
        REQUEST_COUNT.labels(status="error").inc()
        logger.error("ingest_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal routing failure")
    finally:
        REQUEST_LATENCY.observe(time.perf_counter() - start)

    background_tasks.add_task(
        _persist_shadow_result,
        request_id, payload.features, payload.true_label, shadow_result,
    )

    return IngestResponse(
        request_id=request_id,
        status="accepted",
        message="Request dispatched to both models in shadow mode.",
        timestamp=datetime.utcnow(),
    )
