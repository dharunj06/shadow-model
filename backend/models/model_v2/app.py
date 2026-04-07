"""
Model V2 — XGBoost (Shadow Model)
Standalone FastAPI microservice on port 8002
"""
import time
from datetime import datetime
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List
from pathlib import Path
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Model V2 — XGBoost", version="1.0.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

MODEL_PATH = Path(__file__).parent / "model_v2.pkl"
model = None
model_reloaded_at: datetime | None = None
MODEL_REQUESTS = Counter("shadow_model_requests_total", "Total prediction requests", ["model_version", "status"])
MODEL_LATENCY = Histogram("shadow_model_inference_latency_seconds", "Model inference latency", ["model_version"], buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5])
MODEL_ERRORS = Counter("shadow_model_service_errors_total", "Model service errors", ["model_version", "error_type"])


@app.on_event("startup")
async def load_model():
    global model
    global model_reloaded_at
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model file not found: {MODEL_PATH}. Run train.py first.")
    model = joblib.load(MODEL_PATH)
    model_reloaded_at = datetime.utcnow()


class PredictRequest(BaseModel):
    features: List[float]


class PredictResponse(BaseModel):
    prediction: int
    probability: float
    model_version: str = "v2"
    latency_ms: float


@app.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    start = time.perf_counter()
    try:
        X = np.array(payload.features).reshape(1, -1)
        pred = int(model.predict(X)[0])
        prob = float(model.predict_proba(X)[0][pred])
        latency_ms = (time.perf_counter() - start) * 1000
        MODEL_REQUESTS.labels(model_version="v2", status="success").inc()
        MODEL_LATENCY.labels(model_version="v2").observe(latency_ms / 1000)
        return PredictResponse(prediction=pred, probability=prob, latency_ms=latency_ms)
    except Exception as e:
        MODEL_REQUESTS.labels(model_version="v2", status="error").inc()
        MODEL_ERRORS.labels(model_version="v2", error_type=type(e).__name__).inc()
        raise HTTPException(status_code=422, detail=f"Prediction failed: {str(e)}")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": "v2",
        "type": "XGBoost",
        "model_path": str(MODEL_PATH),
        "reloaded_at": model_reloaded_at.isoformat() if model_reloaded_at else None,
    }


@app.post("/upload-model")
async def upload_model(file: UploadFile = File(...)):
    """Upload a new model artifact and hot-reload without restarting the service."""
    global model
    global model_reloaded_at

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    lowered = file.filename.lower()
    if not (lowered.endswith(".pkl") or lowered.endswith(".joblib")):
        raise HTTPException(status_code=400, detail="Only .pkl or .joblib files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    tmp_path = MODEL_PATH.with_suffix(".upload.tmp")
    try:
        tmp_path.write_bytes(content)
        new_model = joblib.load(tmp_path)

        # Swap the artifact atomically and then switch in-memory model reference.
        tmp_path.replace(MODEL_PATH)
        model = new_model
        model_reloaded_at = datetime.utcnow()
    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Invalid model artifact: {str(exc)}")

    return {
        "status": "ok",
        "model_version": "v2",
        "filename": file.filename,
        "size_bytes": len(content),
        "reloaded_at": model_reloaded_at.isoformat(),
    }


class LoadModelRequest(BaseModel):
    model_path: str


@app.post("/load-model")
async def load_model(request: LoadModelRequest):
    """Load a model from a specified file path and hot-reload without restarting."""
    global model
    global model_reloaded_at

    model_path = Path(request.model_path)
    
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model file not found: {request.model_path}")
    
    if not (model_path.suffix in [".pkl", ".joblib"]):
        raise HTTPException(status_code=400, detail="Only .pkl or .joblib files are supported")
    
    try:
        new_model = joblib.load(model_path)
        model = new_model
        model_reloaded_at = datetime.utcnow()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid model artifact: {str(exc)}")
    
    return {
        "status": "ok",
        "model_version": "v2",
        "filename": model_path.name,
        "model_path": str(model_path),
        "reloaded_at": model_reloaded_at.isoformat(),
    }


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
