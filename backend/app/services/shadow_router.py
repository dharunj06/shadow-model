import asyncio
import time
from typing import Optional, Tuple
import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import MODEL_LATENCY, MODEL_ERROR_COUNT

logger = get_logger(__name__)

TIMEOUT = httpx.Timeout(10.0, connect=3.0)


async def call_model(
    client: httpx.AsyncClient,
    url: str,
    version: str,
    features: list,
) -> Tuple[Optional[dict], float, Optional[str]]:
    """Call a single model service. Returns (result, latency_ms, error_str)."""
    start = time.perf_counter()
    try:
        response = await client.post(
            f"{url}/predict",
            json={"features": features},
            timeout=TIMEOUT,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        response.raise_for_status()
        MODEL_LATENCY.labels(model_version=version).observe(latency_ms / 1000)
        return response.json(), latency_ms, None

    except httpx.TimeoutException:
        latency_ms = (time.perf_counter() - start) * 1000
        MODEL_ERROR_COUNT.labels(model_version=version, error_type="timeout").inc()
        logger.warning("model_timeout", model=version)
        return None, latency_ms, "TimeoutError"

    except httpx.HTTPStatusError as e:
        latency_ms = (time.perf_counter() - start) * 1000
        MODEL_ERROR_COUNT.labels(model_version=version, error_type="http_error").inc()
        logger.error("model_http_error", model=version, status=e.response.status_code)
        return None, latency_ms, f"HTTPError:{e.response.status_code}"

    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        MODEL_ERROR_COUNT.labels(model_version=version, error_type="unknown").inc()
        logger.error("model_call_failed", model=version, error=str(e))
        return None, latency_ms, f"Error:{type(e).__name__}"


async def shadow_dispatch(features: list) -> dict:
    """
    Send the same input to both model_v1 (production) and model_v2 (shadow)
    concurrently. Returns structured result — no model output is exposed to callers.
    """
    async with httpx.AsyncClient() as client:
        v1_task = call_model(client, settings.MODEL_V1_URL, "v1", features)
        v2_task = call_model(client, settings.MODEL_V2_URL, "v2", features)

        (v1_result, v1_latency, v1_error), (v2_result, v2_latency, v2_error) = await asyncio.gather(
            v1_task, v2_task
        )

    return {
        "v1": {
            "result": v1_result,
            "latency_ms": v1_latency,
            "error": v1_error,
            "is_error": v1_error is not None,
        },
        "v2": {
            "result": v2_result,
            "latency_ms": v2_latency,
            "error": v2_error,
            "is_error": v2_error is not None,
        },
    }
