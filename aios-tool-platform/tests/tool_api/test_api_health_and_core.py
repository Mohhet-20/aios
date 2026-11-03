import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
@pytest.mark.asyncio
async def test_health_liveness_probe(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_health_readiness_probe(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["components"][0]["name"] == "database"
    assert body["components"][0]["healthy"] is True



@pytest.mark.asyncio
async def test_openapi_loads(client):
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"] == "AIOS Enterprise Tool Execution & Integration Platform"


@pytest.mark.asyncio
async def test_requires_actor_header_for_actor_scoped_endpoints(app):
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/registry/recently-used")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_workspace_crud(client):
    r = await client.post("/api/v1/workspaces", json={"name": "Acme Co", "slug": "acme-co", "organization_id": "org-1"})
    assert r.status_code == 201, r.text
    ws = r.json()
    assert ws["name"] == "Acme Co"

    r = await client.get(f"/api/v1/workspaces/{ws['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == ws["id"]

    r = await client.get("/api/v1/workspaces", params={"organization_id": "org-1"})
    assert r.status_code == 200
    assert any(w["id"] == ws["id"] for w in r.json())


@pytest.mark.asyncio
async def test_not_found_maps_to_404(client):
    r = await client.get("/api/v1/tools/does-not-exist")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_category_registry_endpoints(client):
    r = await client.get("/api/v1/registry/categories")
    assert r.status_code == 200
    keys = {c["key"] for c in r.json()}
    assert "web_search" in keys and "python_execution" in keys
    assert len(keys) == 37

    r = await client.get("/api/v1/registry/categories/web_search")
    assert r.status_code == 200
    assert r.json()["connector_key"] == "web_search"
