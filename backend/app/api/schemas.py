from typing import Optional, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Ingest ──────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    features: List[float] = Field(..., description="Feature vector for prediction")
    true_label: Optional[int] = Field(None, description="Ground truth label (optional)")
    metadata: Optional[dict] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    request_id: UUID
    status: str
    message: str
    timestamp: datetime


# ─── Prediction ───────────────────────────────────────────────────────────────

class PredictionSchema(BaseModel):
    id: UUID
    request_id: UUID
    model_version: str
    prediction: Optional[int]
    probability: Optional[float]
    latency_ms: Optional[float]
    is_error: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Metrics ─────────────────────────────────────────────────────────────────

class MetricSchema(BaseModel):
    id: UUID
    recorded_at: datetime
    model_version: str
    accuracy: Optional[float]
    agreement_rate: Optional[float]
    avg_latency_ms: Optional[float]
    error_rate: Optional[float]
    sample_count: int
    promotion_status: str
    drift_score: Optional[float]

    class Config:
        from_attributes = True


# ─── Errors ──────────────────────────────────────────────────────────────────

class ErrorLogSchema(BaseModel):
    id: UUID
    request_id: Optional[UUID]
    model_version: Optional[str]
    error_type: str
    message: str
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Request Log ─────────────────────────────────────────────────────────────

class RequestSchema(BaseModel):
    id: UUID
    created_at: datetime
    status: str
    true_label: Optional[int]
    predictions: List[PredictionSchema] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ─── Evaluation ──────────────────────────────────────────────────────────────

class EvaluationResult(BaseModel):
    v1_accuracy: Optional[float]
    v2_accuracy: Optional[float]
    agreement_rate: float
    v1_avg_latency_ms: float
    v2_avg_latency_ms: float
    v1_error_rate: float
    v2_error_rate: float
    drift_score: Optional[float]
    promotion_candidate: bool
    sample_count: int
    labeled_sample_count: int = 0


class ModelEvaluationMetrics(BaseModel):
    """Metrics returned during model comparison."""
    v1_accuracy: Optional[float] = Field(None, description="Production model accuracy")
    v2_accuracy: Optional[float] = Field(None, description="Shadow model accuracy")
    latency_v1: float = Field(..., description="Production model avg latency (ms)")
    latency_v2: float = Field(..., description="Shadow model avg latency (ms)")
    agreement_rate: float = Field(..., description="Rate at which both models agree")
    error_rate: float = Field(..., description="Combined error rate")
    drift_score: Optional[float] = Field(None, description="Data distribution drift score")


class ModelEvaluationDecision(BaseModel):
    """Interactive model evaluation decision."""
    decision: str = Field(..., description="PROMOTE_MODEL_V2 or KEEP_MODEL_V1")
    confidence_score: float = Field(..., description="Confidence (0.0-1.0)")
    reasoning: List[str] = Field(default_factory=list, description="Explanation of decision")
    metrics: ModelEvaluationMetrics
    recommended_action: str = Field(..., description="Next recommended action")
    evaluation_timestamp: datetime
    sample_count: int = Field(..., description="Number of samples evaluated")


class ModelUploadResponse(BaseModel):
    status: str
    message: str
    model_version: str
    filename: str
    size_bytes: int
    reloaded_at: datetime


class ModelUploadSchema(BaseModel):
    """Schema for uploaded models in history list."""
    id: str = Field(..., description="Upload ID (UUID)")
    filename: str
    model_version: str
    size_bytes: int
    uploaded_at: datetime
    is_active: bool
    accuracy: Optional[float] = None
    
    class Config:
        from_attributes = True


class ModelUploadListResponse(BaseModel):
    """List of all uploaded models."""
    uploads: List[ModelUploadSchema]
    total_count: int
    active_model_id: Optional[str] = None


# ─── Auth ─────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str
