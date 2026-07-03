import pytest


@pytest.mark.anyio
async def test_health_returns_ok(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data


@pytest.mark.anyio
async def test_health_version_format(client):
    response = await client.get("/api/v1/health")
    version = response.json()["version"]
    parts = version.split(".")
    assert len(parts) == 3, f"Expected semver, got: {version}"


@pytest.mark.anyio
async def test_unknown_route_returns_json_404(client):
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_docs_available_in_dev(client):
    response = await client.get("/docs")
    assert response.status_code == 200
