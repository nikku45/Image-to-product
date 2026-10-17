import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_ok(client: AsyncClient):
    """Verify that GET /api/health responds with status 200 and 'ok'."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data
    assert "gemini_configured" in data
    assert "serpapi_configured" in data


@pytest.mark.asyncio
async def test_root_endpoint_returns_metadata(client: AsyncClient):
    """Verify that GET / returns API metadata and documentation links."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Image-to-Amazon.in Product Matcher API"
    assert data["health_url"] == "/api/health"
