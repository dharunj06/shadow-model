import numpy as np
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Prediction, Request, Metric, PromotionStatus
from app.core.config import settings
from app.core.metrics import (
    MODEL_AGREEMENT_RATE, MODEL_ACCURACY, PROMOTION_CANDIDATE
)
from app.core.logging import get_logger
from datetime import datetime, timedelta
from scipy import stats

logger = get_logger(__name__)


# ─── Drift Detection ──────────────────────────────────────────────────────────

def compute_ks_drift(ref: List[float], curr: List[float]) -> float:
    """Kolmogorov-Smirnov test for distribution drift."""
    if len(ref) < 10 or len(curr) < 10:
        return 0.0
    stat, p_value = stats.ks_2samp(ref, curr)
    return round(float(stat), 4)


# ─── Core Evaluation ──────────────────────────────────────────────────────────

async def evaluate_models(db: AsyncSession, window_hours: int = 24) -> dict:
    """
    Evaluate v1 vs v2 over a rolling window.
    Returns accuracy, agreement, latency, error rate, drift score.
    """
    since = datetime.utcnow() - timedelta(hours=window_hours)

    # Fetch predictions within window and align outputs by request_id so the
    # comparison always uses the same input for both models.
    result = await db.execute(
        select(Prediction, Request.true_label)
        .join(Request, Prediction.request_id == Request.id)
        .where(Prediction.created_at >= since)
    )
    rows = result.all()

    grouped: dict = {}
    v1_preds, v2_preds = [], []
    v1_labels, v2_labels = [], []
    v1_latencies, v2_latencies = [], []
    v1_errors, v2_errors = 0, 0

    for pred, true_label in rows:
        bucket = grouped.setdefault(pred.request_id, {"true_label": true_label})
        if bucket.get("true_label") is None and true_label is not None:
            bucket["true_label"] = true_label
        bucket[pred.model_version] = pred

        if pred.model_version == "v1" and pred.prediction is not None:
            v1_preds.append(pred.prediction)
            v1_latencies.append(pred.latency_ms or 0.0)
            if pred.is_error:
                v1_errors += 1
            if true_label is not None:
                v1_labels.append((pred.prediction, true_label))
        elif pred.model_version == "v2" and pred.prediction is not None:
            v2_preds.append(pred.prediction)
            v2_latencies.append(pred.latency_ms or 0.0)
            if pred.is_error:
                v2_errors += 1
            if true_label is not None:
                v2_labels.append((pred.prediction, true_label))

    paired_requests = [
        entry
        for entry in grouped.values()
        if entry.get("v1") is not None and entry.get("v2") is not None
    ]

    paired_labeled_requests = [
        entry
        for entry in paired_requests
        if entry.get("true_label") is not None
        and entry["v1"].prediction is not None
        and entry["v2"].prediction is not None
    ]

    # Agreement rate
    agreement = 0
    if paired_requests:
        matched = 0
        for entry in paired_requests:
            v1_pred = entry["v1"].prediction
            v2_pred = entry["v2"].prediction
            if v1_pred is not None and v2_pred is not None and v1_pred == v2_pred:
                matched += 1
        agreement = matched / len(paired_requests)

    # Accuracy
    v1_acc = None
    if v1_labels:
        v1_acc = sum(1 for pred, label in v1_labels if pred == label) / len(v1_labels)

    v2_acc = None
    if v2_labels:
        v2_acc = sum(1 for pred, label in v2_labels if pred == label) / len(v2_labels)

    # Latencies
    v1_avg_latency = float(np.mean(v1_latencies)) if v1_latencies else 0.0
    v2_avg_latency = float(np.mean(v2_latencies)) if v2_latencies else 0.0

    # Error rates
    v1_error_rate = v1_errors / len(v1_preds) if v1_preds else 0.0
    v2_error_rate = v2_errors / len(v2_preds) if v2_preds else 0.0

    # Drift on probabilities
    v1_probs_result = await db.execute(
        select(Prediction.probability)
        .where(Prediction.model_version == "v1")
        .where(Prediction.created_at < since - timedelta(hours=window_hours))
        .limit(500)
    )
    v1_ref = [r[0] for r in v1_probs_result if r[0] is not None]

    v1_curr_result = await db.execute(
        select(Prediction.probability)
        .where(Prediction.model_version == "v1")
        .where(Prediction.created_at >= since)
        .limit(500)
    )
    v1_curr = [r[0] for r in v1_curr_result if r[0] is not None]

    drift_score = compute_ks_drift(v1_ref, v1_curr)

    # Promotion logic
    promotion_candidate = False
    sample_count = len(paired_requests)
    labeled_sample_count = len(paired_labeled_requests)
    if labeled_sample_count >= settings.PROMOTION_THRESHOLD:
        if v2_acc is not None and v1_acc is not None:
            if (v2_acc - v1_acc) >= settings.PROMOTION_ACCURACY_DELTA:
                promotion_candidate = True
                logger.info("promotion_candidate_detected", v1_acc=v1_acc, v2_acc=v2_acc)

    # Update Prometheus gauges
    MODEL_AGREEMENT_RATE.set(agreement)
    if v1_acc is not None:
        MODEL_ACCURACY.labels(model_version="v1").set(v1_acc)
    if v2_acc is not None:
        MODEL_ACCURACY.labels(model_version="v2").set(v2_acc)
    PROMOTION_CANDIDATE.set(1 if promotion_candidate else 0)

    # Persist metric snapshot
    metric = Metric(
        recorded_at=datetime.utcnow(),
        model_version="comparison",
        accuracy=v2_acc,
        agreement_rate=agreement,
        avg_latency_ms=v2_avg_latency,
        error_rate=v2_error_rate,
        sample_count=sample_count,
        promotion_status=PromotionStatus.CANDIDATE if promotion_candidate else PromotionStatus.NONE,
        drift_score=drift_score,
    )
    db.add(metric)
    await db.flush()

    return {
        "v1_accuracy": v1_acc,
        "v2_accuracy": v2_acc,
        "agreement_rate": round(agreement, 4),
        "v1_avg_latency_ms": round(v1_avg_latency, 2),
        "v2_avg_latency_ms": round(v2_avg_latency, 2),
        "v1_error_rate": round(v1_error_rate, 4),
        "v2_error_rate": round(v2_error_rate, 4),
        "drift_score": drift_score,
        "promotion_candidate": promotion_candidate,
        "sample_count": sample_count,
        "labeled_sample_count": labeled_sample_count,
    }


async def get_metrics_history(db: AsyncSession, limit: int = 100):
    result = await db.execute(
        select(Metric)
        .order_by(Metric.recorded_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ─── Promotion Decision Logic ─────────────────────────────────────────────────

async def compute_promotion_decision(db: AsyncSession, window_hours: int = 24) -> dict:
    """
    Compute interactive promotion decision based on:
    - Shadow accuracy > production accuracy
    - Shadow latency <= production latency * 1.2
    - Error rate < 5%
    
    Returns decision dict with reasoning and confidence score.
    """
    # Get evaluation metrics
    eval_result = await evaluate_models(db, window_hours=window_hours)
    
    v1_acc = eval_result.get("v1_accuracy")
    v2_acc = eval_result.get("v2_accuracy")
    v1_latency = eval_result.get("v1_avg_latency_ms", 0.0)
    v2_latency = eval_result.get("v2_avg_latency_ms", 0.0)
    v1_error_rate = eval_result.get("v1_error_rate", 0.0)
    v2_error_rate = eval_result.get("v2_error_rate", 0.0)
    agreement_rate = eval_result.get("agreement_rate", 0.0)
    drift_score = eval_result.get("drift_score", 0.0)
    sample_count = eval_result.get("sample_count", 0)
    
    # Decision thresholds
    LATENCY_RATIO_THRESHOLD = 1.2
    ERROR_RATE_THRESHOLD = 0.05  # 5%
    MIN_ACCURACY_SAMPLES = 10
    
    decision = "KEEP_MODEL_V1"
    confidence = 0.0
    reasoning = []
    recommended_action = "Continue monitoring production model"
    factors = []
    
    # Accuracy check
    labeled_sample_count = eval_result.get("labeled_sample_count", 0)
    has_accuracy_data = v1_acc is not None and v2_acc is not None and labeled_sample_count >= MIN_ACCURACY_SAMPLES
    
    if has_accuracy_data:
        accuracy_delta = v2_acc - v1_acc
        factors.append({
            "name": "Accuracy improvement",
            "v1": v1_acc,
            "v2": v2_acc,
            "delta": accuracy_delta,
            "positive": accuracy_delta > 0.0
        })
        
        if accuracy_delta > 0.0:
              reasoning.append(f"[PASS] Shadow model accuracy ({v2_acc:.2%}) > Production ({v1_acc:.2%}) by {accuracy_delta:.2%}")
        else:
              reasoning.append(f"[FAIL] Shadow model accuracy ({v2_acc:.2%}) <= Production ({v1_acc:.2%})")
    else:
           reasoning.append(f"[WARN] Insufficient labeled samples ({labeled_sample_count}/{MIN_ACCURACY_SAMPLES})")
    
    # Latency check
    if v1_latency > 0:
        latency_ratio = v2_latency / v1_latency
        factors.append({
            "name": "Latency efficiency",
            "v1": v1_latency,
            "v2": v2_latency,
            "ratio": latency_ratio,
            "positive": latency_ratio <= LATENCY_RATIO_THRESHOLD
        })
        
        if latency_ratio <= LATENCY_RATIO_THRESHOLD:
              reasoning.append(f"[PASS] Shadow model latency ({v2_latency:.1f}ms) within {LATENCY_RATIO_THRESHOLD}x threshold (ratio: {latency_ratio:.2f}x)")
        else:
              reasoning.append(f"[FAIL] Shadow model latency ({v2_latency:.1f}ms) exceeds {LATENCY_RATIO_THRESHOLD}x threshold (ratio: {latency_ratio:.2f}x)")
    
    # Error rate check
    max_error_rate = max(v1_error_rate, v2_error_rate)
    factors.append({
        "name": "Error rate stability",
        "v1": v1_error_rate,
        "v2": v2_error_rate,
        "max": max_error_rate,
        "positive": max_error_rate < ERROR_RATE_THRESHOLD
    })
    
    if max_error_rate < ERROR_RATE_THRESHOLD:
           reasoning.append(f"[PASS] Error rates acceptable: v1={v1_error_rate:.2%}, v2={v2_error_rate:.2%}")
    else:
           reasoning.append(f"[FAIL] Error rate too high: v1={v1_error_rate:.2%}, v2={v2_error_rate:.2%}")
    
    # Agreement rate (informational)
    factors.append({
        "name": "Model agreement",
        "value": agreement_rate,
        "positive": True
    })
    reasoning.append(f"[INFO] Models agree on {agreement_rate:.1%} of predictions")
    
    # Compute promotion decision
    accuracy_ok = (v1_acc is not None and v2_acc is not None and (v2_acc - v1_acc) > 0.0) or not has_accuracy_data
    latency_ok = (v1_latency == 0 or (v2_latency / v1_latency) <= LATENCY_RATIO_THRESHOLD)
    error_ok = max_error_rate < ERROR_RATE_THRESHOLD
    
    positive_factors = sum(1 for f in factors if f.get("positive", False))
    total_factors = len(factors)
    
    if accuracy_ok and latency_ok and error_ok:
        decision = "PROMOTE_MODEL_V2"
        recommended_action = "✅ Shadow model ready for promotion. Consider rolling it to production."
        confidence = min(0.95, 0.5 + (positive_factors / total_factors) * 0.45)
    else:
        confidence = max(0.1, (positive_factors / total_factors) * 0.4)
    
    # Drift warning
    if drift_score and drift_score > 0.1:
           reasoning.append(f"[WARN] High data drift detected (KS score: {drift_score:.4f}). Monitor for distribution shift.")
    
    return {
        "decision": decision,
        "confidence_score": round(confidence, 3),
        "reasoning": reasoning,
        "metrics": {
            "v1_accuracy": v1_acc,
            "v2_accuracy": v2_acc,
            "latency_v1": round(v1_latency, 2),
            "latency_v2": round(v2_latency, 2),
            "agreement_rate": round(agreement_rate, 4),
            "error_rate": round(max(v1_error_rate, v2_error_rate), 4),
            "drift_score": drift_score,
        },
        "recommended_action": recommended_action,
        "evaluation_timestamp": datetime.utcnow().isoformat(),
        "sample_count": sample_count,
        "factors": factors,
    }
