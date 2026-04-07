# 🔮 ShadowML — Shadow Mode-Based ML Model Evaluation System

> **Production-grade MLOps platform** for safe, zero-risk model deployment using shadow mode evaluation. Internal model comparison with no user-facing prediction leakage.

![Architecture](https://img.shields.io/badge/Architecture-Microservices-6366f1?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11-3b82f6?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-10b981?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker)

---

## 📐 Architecture Overview

```
                        ┌─────────────────────────────────────┐
  User Request ────────▶│      API Gateway (FastAPI :8000)    │
                        │   POST /ingest → returns metadata   │
                        └────────────┬────────────────────────┘
                                     │ Shadow Dispatch (async)
                     ┌───────────────┴──────────────┐
                     ▼                              ▼
          ┌──────────────────┐          ┌──────────────────┐
          │  Model V1 :8001  │          │  Model V2 :8002  │
          │ LogisticRegress  │          │    XGBoost       │
          │  (Production)    │          │    (Shadow)      │
          └────────┬─────────┘          └────────┬─────────┘
                   │                             │
                   └──────────┬──────────────────┘
                              ▼
                   ┌─────────────────────┐
                   │   Logging Service   │
                   │   (PostgreSQL DB)   │
                   └────────┬────────────┘
                            ▼
                   ┌─────────────────────┐
                   │  Evaluation Engine  │
                   │  Accuracy, Latency, │
                   │  Agreement, Drift   │
                   └────────┬────────────┘
                            ▼
         ┌──────────────────┴──────────────────┐
         │           Monitoring                │
         │  Prometheus :9090 + Grafana :3001   │
         └──────────────────┬──────────────────┘
                            ▼
                   ┌─────────────────────┐
                   │  React Dashboard    │
                   │    :3000            │
                   └─────────────────────┘
```

---

## 🧱 Project Structure

```
mlops/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── ingest.py        # POST /ingest — shadow dispatch
│   │   │   │   ├── evaluation.py    # GET /evaluate, /metrics/history
│   │   │   │   ├── logs.py          # GET /requests, /errors
│   │   │   │   └── health.py        # GET /health
│   │   │   └── schemas.py           # Pydantic models
│   │   ├── core/
│   │   │   ├── config.py            # Settings (env-based)
│   │   │   ├── metrics.py           # Prometheus counters/histograms
│   │   │   ├── logging.py           # Structured logging (structlog)
│   │   │   └── security.py          # JWT auth utilities
│   │   ├── db/
│   │   │   ├── session.py           # Async SQLAlchemy engine
│   │   │   └── models.py            # ORM: Request, Prediction, Metric, Error
│   │   ├── services/
│   │   │   ├── shadow_router.py     # Concurrent model dispatch
│   │   │   ├── log_service.py       # DB write helpers
│   │   │   └── evaluator.py         # Evaluation engine + drift detection
│   │   └── main.py                  # FastAPI app + lifespan + scheduler
│   ├── models/
│   │   ├── model_v1/
│   │   │   ├── app.py               # Logistic Regression microservice
│   │   │   └── train.py             # Training script + MLflow logging
│   │   └── model_v2/
│   │       ├── app.py               # XGBoost microservice
│   │       └── train.py             # Training script + MLflow logging
│   ├── tests/
│   │   ├── test_api.py              # Integration tests
│   │   └── test_models.py           # Model accuracy/shape tests
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/client.js            # Axios API wrapper
│   │   ├── pages/
│   │   │   ├── Overview.jsx         # KPI cards + trend charts
│   │   │   ├── ModelComparison.jsx  # Radar + bar charts + table
│   │   │   ├── RequestLogs.jsx      # Paginated log table
│   │   │   └── ErrorMonitor.jsx     # Error tracking + severity filter
│   │   ├── App.jsx                  # Router + sidebar layout
│   │   ├── App.css                  # Layout styles
│   │   └── index.css                # Global design system
│   ├── nginx.conf
│   ├── vite.config.js
│   └── package.json
├── docker/
│   ├── Dockerfile.model_v1
│   ├── Dockerfile.model_v2
│   └── Dockerfile.frontend
├── k8s/
│   ├── namespace.yml
│   ├── secrets.yml
│   ├── postgres.yml
│   ├── backend.yml
│   ├── model-v1.yml
│   ├── model-v2.yml
│   ├── frontend.yml
│   └── istio/
│       └── virtual-service.yml      # Istio traffic mirroring + DestinationRule
├── monitoring/
│   ├── prometheus.yml
│   ├── alert_rules.yml
│   └── grafana/provisioning/
│       └── datasources/prometheus.yml
├── .github/workflows/
│   └── ci-cd.yml                    # Lint → Test → Build → Deploy
└── docker-compose.yml
```

Implementation note: the model services live under [backend/models](backend/models) in this repo, and the deployment workflow rewrites the placeholder image registry paths before applying the Kubernetes manifests.

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Docker Desktop ≥ 24
- Python 3.11+
- Node.js 20+

### 1. Clone & Configure
```bash
git clone <repo-url>
cd mlops

# Copy backend env
cp backend/.env.example backend/.env
```

### 2. Train Both Models First
```bash
cd backend

# Install deps
pip install -r requirements.txt

# Start MLflow (needed for logging)
mlflow server --host 0.0.0.0 --port 5000 &

# Train Model V1 (Logistic Regression)
python models/model_v1/train.py

# Train Model V2 (XGBoost)
python models/model_v2/train.py
```

### 3. Start All Services (Docker)
```bash
# From project root
docker-compose up --build
```

| Service      | URL                          |
|-------------|-------------------------------|
| API Gateway  | http://localhost:8000         |
| API Docs     | http://localhost:8000/docs    |
| Model V1     | http://localhost:8001         |
| Model V2     | http://localhost:8002         |
| Frontend     | http://localhost:3000         |
| MLflow       | http://localhost:5000         |
| Prometheus   | http://localhost:9090         |
| Grafana      | http://localhost:3001 (admin/admin123) |

### 4. Run Backend Locally (without Docker)
```bash
cd backend

# Start PostgreSQL separately or use Docker:
docker run -d -e POSTGRES_PASSWORD=password -e POSTGRES_DB=shadowml -p 5432:5432 postgres:16-alpine

# Run model services
uvicorn models.model_v1.app:app --port 8001 &
uvicorn models.model_v2.app:app --port 8002 &

# Run API gateway
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Run Frontend Locally
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## 🔌 API Reference

### POST `/api/v1/ingest`
Submit input for shadow evaluation. **No model outputs are returned.**
```json
// Request
{
  "features": [17.99, 10.38, 122.8, 1001.0, ...],  // 30 floats (breast cancer)
  "true_label": 1  // optional ground truth
}

// Response (metadata only)
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Request dispatched to both models in shadow mode.",
  "timestamp": "2026-04-06T17:30:00Z"
}
```

### GET `/api/v1/evaluate?window_hours=24`
On-demand model evaluation over rolling window.
```json
{
  "v1_accuracy": 0.9561,
  "v2_accuracy": 0.9737,
  "agreement_rate": 0.9649,
  "v1_avg_latency_ms": 8.4,
  "v2_avg_latency_ms": 12.1,
  "v1_error_rate": 0.0,
  "v2_error_rate": 0.0,
  "drift_score": 0.042,
  "promotion_candidate": true,
  "sample_count": 150
}
```

### GET `/api/v1/requests?limit=50&offset=0`
Paginated request log with internal predictions.

### GET `/api/v1/errors?limit=50`
Recent error log across all model services.

### GET `/api/v1/metrics/history?limit=100`
Historical evaluation snapshot records.

### GET `/api/v1/health`
Service health check.

---

## 📊 Evaluation Engine

The evaluator runs **automatically every hour** (APScheduler) and on-demand:

| Metric | Description |
|--------|-------------|
| **Accuracy** | Correct predictions / total (requires `true_label`) |
| **Agreement Rate** | % of requests where V1 and V2 agree |
| **Avg Latency** | Rolling mean inference time per model |
| **Error Rate** | % of failed model calls |
| **Drift Score** | Kolmogorov-Smirnov statistic on output probabilities |

### Auto-Promotion Logic
```
IF sample_count >= PROMOTION_THRESHOLD (100)
AND v2_accuracy - v1_accuracy >= PROMOTION_ACCURACY_DELTA (0.02)
→ mark as PromotionStatus.CANDIDATE
→ trigger Prometheus alert
→ dashboard shows promotion banner
```

---

## 🐳 Docker Services

```bash
docker-compose up          # Start all services
docker-compose down        # Stop all
docker-compose logs -f backend   # Follow backend logs
docker-compose ps          # Service status
```

---

## ☸️ Kubernetes Deployment

```bash
# Apply namespace (Istio-enabled)
kubectl apply -f k8s/namespace.yml

# Deploy services
kubectl apply -f k8s/backend.yml
kubectl apply -f k8s/model-v1.yml
kubectl apply -f k8s/model-v2.yml

# Istio traffic mirroring
kubectl apply -f k8s/istio/virtual-service.yml

# Check status
kubectl get pods -n shadowml
kubectl get svc -n shadowml
```

> Replace `YOUR_ORG` in k8s manifests with your GitHub org before applying.
> Set `KUBE_CONFIG` secret in GitHub Actions for automated deployment.

---

## 🧪 Running Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# API tests only
pytest tests/test_api.py -v

# Model validation tests (requires trained models)
pytest tests/test_models.py -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing
```

---

## 📈 Monitoring

### Prometheus Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `shadow_request_total` | Counter | Total requests by status |
| `shadow_request_latency_seconds` | Histogram | End-to-end latency |
| `shadow_model_latency_seconds` | Histogram | Per-model latency |
| `shadow_model_errors_total` | Counter | Errors by model + type |
| `shadow_model_agreement_rate` | Gauge | Rolling agreement % |
| `shadow_model_accuracy` | Gauge | Rolling accuracy per model |
| `shadow_promotion_candidate` | Gauge | 1 if V2 is promotion-ready |

### Grafana
1. Navigate to http://localhost:3001 (admin / admin123)
2. Prometheus datasource is auto-provisioned
3. Import dashboard from `monitoring/grafana/`

### Alerts (prometheus)
- `HighErrorRate` — model error rate > 5% for 2 min
- `HighLatency` — P95 > 2s for 5 min
- `PromotionCandidate` — V2 outperforms V1
- `LowAgreementRate` — agreement < 70% for 10 min

---

## 🔁 CI/CD Pipeline

GitHub Actions runs on every push to `main`:

```
Push to main
    ↓
backend-test   ←── pytest + ruff lint + postgres service
frontend-test  ←── npm build + eslint
    ↓ (both pass)
build-images   ←── docker build + push to GHCR
    ↓ (main only)
deploy         ←── kubectl apply all manifests
```

Required GitHub secrets:
- `KUBE_CONFIG` — base64-encoded kubeconfig

---

## 🔒 Security Notes

- Change `SECRET_KEY` in production `.env`
- JWT tokens expire in 60 minutes (configurable)
- No model predictions are ever returned to the API caller
- CORS is restricted to known frontend origins in production

---

## 📦 MLflow Experiment Tracking

Both model training scripts log to MLflow:
```bash
# View experiments
mlflow ui --port 5000
# → http://localhost:5000
```

Tracked per run:
- Parameters (model type, hyperparameters)
- Metrics (accuracy, classification report)
- Model artifacts (serialized pipeline)

---

## 🙌 Tech Stack

| Layer | Technology |
|-------|-----------|
| API Gateway | FastAPI 0.111, Uvicorn |
| ML Models | Scikit-learn (LR), XGBoost |
| Database | PostgreSQL 16 + SQLAlchemy 2 async |
| Experiment Tracking | MLflow 2.12 |
| Monitoring | Prometheus + Grafana |
| Frontend | React 18, Recharts, React Router |
| Build | Vite 5 |
| Containers | Docker, Docker Compose |
| Orchestration | Kubernetes + Istio |
| CI/CD | GitHub Actions |
| Logging | structlog + rich |
| Scheduling | APScheduler |
