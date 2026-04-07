import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Integer,
    Text, JSON, ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum


class SeverityLevel(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class PromotionStatus(str, enum.Enum):
    NONE = "NONE"
    CANDIDATE = "CANDIDATE"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"


class Request(Base):
    __tablename__ = "requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    input_data = Column(JSON, nullable=False)
    status = Column(String(32), default="success")
    true_label = Column(Integer, nullable=True)

    predictions = relationship("Prediction", back_populates="request", cascade="all, delete-orphan")
    errors = relationship("ErrorLog", back_populates="request", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, index=True)
    model_version = Column(String(32), nullable=False)
    prediction = Column(Integer, nullable=True)
    probability = Column(Float, nullable=True)
    raw_output = Column(JSON, nullable=True)
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_error = Column(Boolean, default=False)

    request = relationship("Request", back_populates="predictions")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    model_version = Column(String(32), nullable=False, index=True)
    accuracy = Column(Float, nullable=True)
    agreement_rate = Column(Float, nullable=True)
    avg_latency_ms = Column(Float, nullable=True)
    error_rate = Column(Float, nullable=True)
    sample_count = Column(Integer, default=0)
    promotion_status = Column(SAEnum(PromotionStatus), default=PromotionStatus.NONE)
    drift_score = Column(Float, nullable=True)


class ErrorLog(Base):
    __tablename__ = "errors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("requests.id", ondelete="SET NULL"), nullable=True, index=True)
    model_version = Column(String(32), nullable=True)
    error_type = Column(String(64), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(SAEnum(SeverityLevel), default=SeverityLevel.ERROR)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    stack_trace = Column(Text, nullable=True)

    request = relationship("Request", back_populates="errors")


class ModelUpload(Base):
    __tablename__ = "model_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(256), nullable=False)
    model_version = Column(String(32), default="v2", nullable=False)
    file_path = Column(String(512), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_active = Column(Boolean, default=False)
    accuracy = Column(Float, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
