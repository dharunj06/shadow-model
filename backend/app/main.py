from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.session import init_db, AsyncSessionLocal
from app.services.evaluator import evaluate_models
from app.api.schemas import IngestRequest, IngestResponse, EvaluationResult, MetricSchema, RequestSchema, ErrorLogSchema, ModelUploadListResponse
from app.api.schemas import ModelEvaluationDecision
from app.api.routes import ingest, evaluation, logs, health
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, BackgroundTasks, Query, UploadFile, File

setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_evaluation():
    async with AsyncSessionLocal() as db:
        try:
            result = await evaluate_models(db, window_hours=24)
            await db.commit()
            logger.info("scheduled_evaluation_complete", result=result)
        except Exception as e:
            logger.error("scheduled_evaluation_failed", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.APP_NAME, env=settings.APP_ENV)
    await init_db()
    scheduler.add_job(scheduled_evaluation, "interval", hours=1, id="eval_job")
    scheduler.start()
    yield
    scheduler.shutdown()
    logger.info("shutdown")


app = FastAPI(
    title="ShadowML — API Gateway",
    description="Shadow Mode-Based ML Model Evaluation System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Prometheus metrics endpoint ─────────────────────────────────────────────
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(evaluation.router)
app.include_router(logs.router)


# ─── Compatibility aliases ──────────────────────────────────────────────────
@app.get("/health")
async def health_alias():
    return await health.health()


@app.post("/ingest", response_model=IngestResponse)
async def ingest_alias(
    payload: IngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await ingest.ingest(payload, background_tasks, db)


@app.get("/evaluate", response_model=EvaluationResult)
async def evaluate_alias(
    window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    return await evaluation.run_evaluation(window_hours=window_hours, db=db)

@app.post("/evaluate-models", response_model=ModelEvaluationDecision)
async def evaluate_models_alias(
    window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Interactive model evaluation and promotion decision."""
    return await evaluation.evaluate_and_decide(window_hours=window_hours, db=db)


@app.post("/models/v2/upload")
async def upload_model_v2_alias(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await evaluation.upload_model_v2(file=file, db=db)

@app.get("/models/v2/uploads", response_model=ModelUploadListResponse)
async def list_uploaded_models_alias(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await evaluation.list_uploaded_models(limit=limit, db=db)

@app.post("/models/v2/load/{model_id}")
async def load_model_alias(model_id: str, db: AsyncSession = Depends(get_db)):
    return await evaluation.load_model_by_id(model_id=model_id, db=db)

@app.get("/metrics/history", response_model=list[MetricSchema])
async def metrics_history_alias(
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await evaluation.metrics_history(limit=limit, db=db)


@app.get("/requests", response_model=list[RequestSchema])
async def requests_alias(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await logs.list_requests(limit=limit, offset=offset, db=db)


@app.get("/errors", response_model=list[ErrorLogSchema])
async def errors_alias(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await logs.list_errors(limit=limit, db=db)


# ─── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "ShadowML API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
    }
