"""
Model V1 — Logistic Regression (Production Model)
Standalone FastAPI microservice on port 8001
"""
import time
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List
from pathlib import Path
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Model V1 — Logistic Regression", version="1.0.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

MODEL_PATH = Path(__file__).parent / "model_v1.pkl"
model = None
MODEL_REQUESTS = Counter("shadow_model_requests_total", "Total prediction requests", ["model_version", "status"])
MODEL_LATENCY = Histogram("shadow_model_inference_latency_seconds", "Model inference latency", ["model_version"], buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5])
MODEL_ERRORS = Counter("shadow_model_service_errors_total", "Model service errors", ["model_version", "error_type"])


@app.on_event("startup")
async def load_model():
    global model
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model file not found: {MODEL_PATH}. Run train.py first.")
    model = joblib.load(MODEL_PATH)


class PredictRequest(BaseModel):
    features: List[float]


class PredictResponse(BaseModel):
    prediction: int
    probability: float
    model_version: str = "v1"
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
        MODEL_REQUESTS.labels(model_version="v1", status="success").inc()
        MODEL_LATENCY.labels(model_version="v1").observe(latency_ms / 1000)
        return PredictResponse(prediction=pred, probability=prob, latency_ms=latency_ms)
    except Exception as e:
        MODEL_REQUESTS.labels(model_version="v1", status="error").inc()
        MODEL_ERRORS.labels(model_version="v1", error_type=type(e).__name__).inc()
        raise HTTPException(status_code=422, detail=f"Prediction failed: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok", "model": "v1", "type": "LogisticRegression"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
