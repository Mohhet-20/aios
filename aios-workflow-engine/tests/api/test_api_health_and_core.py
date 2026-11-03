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
    assert r.json()["info"]["title"] == "AIOS Enterprise Workflow Orchestration Engine"


@pytest.mark.asyncio
async def test_requires_actor_header(app):
    """Most routers don't need caller identity for pure CRUD (e.g. workspace
    creation), but any endpoint wired through `get_current_actor_id` — like
    granting an RBAC role, which records who granted it — must 401 without
    the X-User-Id header."""
    import httpx
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/v1/rbac/grants", json={
            "principal_id": "user-1", "resource_type": "workspace", "resource_id": "ws-1", "role": "admin",
        })
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
async def test_node_type_registry_endpoints(client):
    r = await client.get("/api/v1/node-types")
    assert r.status_code == 200
    keys = {n["key"] for n in r.json()}
    assert "start" in keys and "end" in keys and "llm_call" in keys
    assert len(keys) == 30

    r = await client.post("/api/v1/node-types/seed")
    assert r.status_code == 201
    assert r.json()["inserted"] >= 0

    r = await client.get("/api/v1/node-definitions")
    assert r.status_code == 200
    assert len(r.json()) == 30


@pytest.mark.asyncio
async def test_not_found_maps_to_404(client):
    r = await client.get("/api/v1/workflows/does-not-exist")
    assert r.status_code == 404
