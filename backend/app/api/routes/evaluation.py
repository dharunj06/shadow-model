from datetime import datetime
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from uuid import UUID
import httpx
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.session import get_db
from app.db.models import ModelUpload
from app.api.schemas import EvaluationResult, MetricSchema, ModelEvaluationDecision, ModelUploadResponse, ModelUploadListResponse, ModelUploadSchema
from app.services.evaluator import evaluate_models, get_metrics_history, compute_promotion_decision
from app.core.logging import get_logger
from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["Evaluation"])
logger = get_logger(__name__)
UPLOAD_DIR = Path("/tmp/shadowml_uploaded_models")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.2f}%"


def _format_ms(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f} ms"


def _log_evaluation_report(result: dict) -> None:
    metrics = result.get("metrics", {})
    reasoning = result.get("reasoning", [])
    decision = result.get("decision", "UNKNOWN")
    recommended_action = result.get("recommended_action", "")

    v1_accuracy = metrics.get("v1_accuracy")
    v2_accuracy = metrics.get("v2_accuracy")
    latency_v1 = metrics.get("latency_v1")
    latency_v2 = metrics.get("latency_v2")
    agreement_rate = metrics.get("agreement_rate")
    error_rate = metrics.get("error_rate")

    if v1_accuracy is not None and v2_accuracy is not None:
        if v2_accuracy > v1_accuracy:
            accuracy_status = "- V2 Better"
        elif v2_accuracy < v1_accuracy:
            accuracy_status = "- V1 Better"
        else:
            accuracy_status = "- V1 Same"
    else:
        accuracy_status = "- Insufficient Data"

    if latency_v1 is not None and latency_v2 is not None:
        latency_status = "✓ Fast" if latency_v2 <= latency_v1 * 1.2 else "✗ Too Slow"
    else:
        latency_status = "-"

    error_status = "✓ Acceptable" if (error_rate or 0.0) < 0.05 else "✗ Too High"

    lines = [
        "Metrics Comparison",
        "Metric\tProduction (V1)\tShadow (V2)\tStatus",
        f"Accuracy\t{_format_percent(v1_accuracy)}\t{_format_percent(v2_accuracy)}\t{accuracy_status}",
        f"Avg Latency\t{_format_ms(latency_v1)}\t{_format_ms(latency_v2)}\t{latency_status}",
        f"Error Rate\t{_format_percent(error_rate)}\t—\t{error_status}",
        f"Model Agreement\t{_format_percent(agreement_rate)}\t—",
        "",
        "Decision Reasoning",
    ]

    for entry in reasoning:
        lines.append("✗" if entry.startswith("[FAIL]") else "✓" if entry.startswith("[PASS]") else "ℹ")
        lines.append(entry)

    if recommended_action:
        lines.append(recommended_action)

    lines.append(f"Decision: {decision}")
    print("\n".join(lines), flush=True)


@router.get("/evaluate", response_model=EvaluationResult)
async def run_evaluation(
    window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Run on-demand model evaluation over a rolling time window."""
    result = await evaluate_models(db, window_hours=window_hours)
    return EvaluationResult(**result)


@router.post("/evaluate-models", response_model=ModelEvaluationDecision)
async def evaluate_and_decide(
    window_hours: int = Query(24, ge=1, le=168),
    model_id: str = Query(None, description="Optional model ID to evaluate"),
    db: AsyncSession = Depends(get_db),
):
    """
    Interactive model comparison endpoint.
    
    Evaluates production (v1) vs shadow (v2) models and returns:
    - Decision: PROMOTE_MODEL_V2 or KEEP_MODEL_V1
    - Confidence score (0.0-1.0)
    - Detailed reasoning for decision
    - Metric comparison
    
    Decision criteria:
    - Shadow accuracy > Production accuracy
    - Shadow latency <= Production latency * 1.2
    - Error rate < 5%
    """
    logger.info("Starting model evaluation", window_hours=window_hours, model_id=model_id)
    
    try:
        result = await compute_promotion_decision(db, window_hours=window_hours)
        logger.info("Model evaluation completed successfully", decision=result.get("decision"), confidence=result.get("confidence_score"))
        _log_evaluation_report(result)
        return ModelEvaluationDecision(**result)
    except Exception as exc:
        logger.error("Model evaluation failed", error=str(exc), error_type=type(exc).__name__, exc_info=True)
        print(f"Evaluation failed: {exc}", flush=True)
        raise HTTPException(status_code=500, detail=f"Evaluation error: {str(exc)}")


@router.post("/models/v2/upload", response_model=ModelUploadResponse)
async def upload_model_v2(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload a new model artifact to model_v2 service and hot-reload it."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    filename = file.filename.lower()
    if not (filename.endswith(".pkl") or filename.endswith(".joblib")):
        raise HTTPException(status_code=400, detail="Only .pkl or .joblib files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Persist uploaded artifacts so users can select historical versions from dashboard.
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    stored_name = f"{timestamp}_{file.filename}"
    stored_path = UPLOAD_DIR / stored_name
    stored_path.write_bytes(content)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.MODEL_V2_URL}/upload-model",
                files={
                    "file": (
                        file.filename,
                        content,
                        file.content_type or "application/octet-stream",
                    )
                },
            )
    except Exception as exc:
        logger.error("model_v2_upload_failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to contact model_v2 service")

    if response.status_code >= 400:
        detail = "Model upload failed"
        try:
            payload = response.json()
            detail = payload.get("detail", detail)
        except Exception:
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)

    reloaded_at = datetime.utcnow()
    
    # Store upload metadata in database
    try:
        upload_record = ModelUpload(
            filename=file.filename,
            model_version="v2",
            file_path=str(stored_path),
            size_bytes=len(content),
            uploaded_at=reloaded_at,
            is_active=True,
            extra_metadata={"original_name": file.filename, "stored_name": stored_name, "content_type": file.content_type}
        )
        db.add(upload_record)
        
        # Mark previous uploads as inactive
        await db.execute(
            update(ModelUpload).where(ModelUpload.model_version == "v2").values(is_active=False)
        )
        upload_record.is_active = True
        
        await db.commit()
        await db.refresh(upload_record)
    except Exception as exc:
        logger.error("db_store_upload_failed", error=str(exc))
        await db.rollback()

    return ModelUploadResponse(
        status="ok",
        message="Model V2 uploaded and reloaded successfully",
        model_version="v2",
        filename=file.filename,
        size_bytes=len(content),
        reloaded_at=reloaded_at,
    )


@router.get("/metrics/history", response_model=list[MetricSchema])
async def metrics_history(
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Return historical metric snapshots."""
    records = await get_metrics_history(db, limit=limit)
    return records


@router.get("/models/v2/uploads", response_model=ModelUploadListResponse)
async def list_uploaded_models(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded model versions with metadata."""
    try:
        query = select(ModelUpload).where(
            ModelUpload.model_version == "v2"
        ).order_by(ModelUpload.uploaded_at.desc()).limit(limit)
        
        result = await db.execute(query)
        uploads = result.scalars().all()
        
        active_model = None
        for upload in uploads:
            if upload.is_active:
                active_model = str(upload.id)
                break
        
        upload_schemas = [
            ModelUploadSchema(
                id=str(upload.id),
                filename=upload.filename,
                model_version=upload.model_version,
                size_bytes=upload.size_bytes,
                uploaded_at=upload.uploaded_at,
                is_active=upload.is_active,
                accuracy=upload.accuracy,
            )
            for upload in uploads
        ]
        
        return ModelUploadListResponse(
            uploads=upload_schemas,
            total_count=len(uploads),
            active_model_id=active_model,
        )
    except Exception as exc:
        logger.error("list_uploads_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to list uploaded models")


@router.post("/models/v2/load/{model_id}")
async def load_model_by_id(
    model_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Load a specific uploaded model by making it the active shadow model."""
    try:
        # Find the model
        query = select(ModelUpload).where(
            (ModelUpload.id == UUID(model_id)) & 
            (ModelUpload.model_version == "v2")
        )
        result = await db.execute(query)
        upload = result.scalar_one_or_none()
        
        if not upload:
            raise HTTPException(status_code=404, detail="Model not found")

        model_path = Path(upload.file_path)
        if not model_path.exists():
            raise HTTPException(status_code=404, detail="Stored model file not found")
        
        # Inform model_v2 service to load this model
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.MODEL_V2_URL}/upload-model",
                    files={
                        "file": (
                            upload.filename,
                            model_path.read_bytes(),
                            "application/octet-stream",
                        )
                    },
                )
                if response.status_code >= 400:
                    raise HTTPException(status_code=502, detail="Failed to load model in model_v2 service")
        except Exception:
            raise HTTPException(status_code=502, detail="Failed to contact model_v2 service")
        
        # Mark as active in DB
        await db.execute(
            update(ModelUpload).where(ModelUpload.model_version == "v2").values(is_active=False)
        )
        upload.is_active = True
        await db.commit()
        
        return {
            "status": "ok",
            "message": f"Model {upload.filename} loaded successfully",
            "model_id": str(upload.id),
            "filename": upload.filename,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("load_model_failed", error=str(exc))
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to load model")
