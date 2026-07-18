import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_health_200(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ("healthy", "degraded")
