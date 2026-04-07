from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    "shadow_request_total",
    "Total ingested requests",
    ["status"],
)

REQUEST_LATENCY = Histogram(
    "shadow_request_latency_seconds",
    "End-to-end request latency",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Model-level metrics
MODEL_LATENCY = Histogram(
    "shadow_model_latency_seconds",
    "Per-model inference latency",
    ["model_version"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

MODEL_ERROR_COUNT = Counter(
    "shadow_model_errors_total",
    "Total model errors",
    ["model_version", "error_type"],
)

MODEL_AGREEMENT_RATE = Gauge(
    "shadow_model_agreement_rate",
    "Rolling agreement rate between v1 and v2",
)

MODEL_ACCURACY = Gauge(
    "shadow_model_accuracy",
    "Rolling accuracy per model",
    ["model_version"],
)

PROMOTION_CANDIDATE = Gauge(
    "shadow_promotion_candidate",
    "1 if shadow model is a promotion candidate",
)
