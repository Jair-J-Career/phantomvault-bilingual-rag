import pytest


@pytest.mark.anyio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "PhantomVault" in data["status"]


@pytest.mark.anyio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "chroma" in data
    assert "google_api_key_present" in data


@pytest.mark.anyio
async def test_ready(client):
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True
