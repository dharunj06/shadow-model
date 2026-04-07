import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.anyio
async def test_ingest_returns_metadata_only():
    """Ensure /ingest never leaks model predictions."""
    mock_shadow = {
        "v1": {"result": {"prediction": 1, "probability": 0.9}, "latency_ms": 12.0, "error": None, "is_error": False},
        "v2": {"result": {"prediction": 1, "probability": 0.95}, "latency_ms": 8.0, "error": None, "is_error": False},
    }

    with patch("app.api.routes.ingest.shadow_dispatch", new=AsyncMock(return_value=mock_shadow)):
        with patch("app.api.routes.ingest._persist_shadow_result", new=AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/ingest",
                    json={"features": [1.0] * 30, "true_label": 1},
                )

    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert data["status"] == "accepted"
    # Critical: no model prediction in response
    assert "prediction" not in data
    assert "probability" not in data
    assert "v1" not in data
    assert "v2" not in data


@pytest.mark.anyio
async def test_ingest_invalid_input():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/ingest", json={"bad_field": "value"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "ShadowML" in response.json()["service"]
