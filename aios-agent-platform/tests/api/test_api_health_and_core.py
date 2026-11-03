import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
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
async def test_workspace_crud(client):
    create_resp = await client.post("/api/v1/workspaces", json={"name": "WS", "slug": "ws-api", "organization_id": "org1"})
    assert create_resp.status_code == 201
    ws = create_resp.json()

    get_resp = await client.get(f"/api/v1/workspaces/{ws['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["slug"] == "ws-api"

    list_resp = await client.get("/api/v1/workspaces", params={"organization_id": "org1"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_workspace_not_found_returns_404(client):
    resp = await client.get("/api/v1/workspaces/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


@pytest.mark.asyncio
async def test_agent_types_seed_and_list(client):
    seed_resp = await client.post("/api/v1/agent-types/seed-builtin")
    assert seed_resp.status_code == 201
    assert len(seed_resp.json()) == 17

    list_resp = await client.get("/api/v1/agent-types")
    assert len(list_resp.json()) == 17

    get_resp = await client.get("/api/v1/agent-types/planner")
    assert get_resp.status_code == 200
    assert get_resp.json()["key"] == "planner"


@pytest.mark.asyncio
async def test_agent_create_lifecycle_and_tool_permissions(client):
    ws = (await client.post("/api/v1/workspaces", json={"name": "WS", "slug": "ws-agent", "organization_id": "org1"})).json()
    await client.post("/api/v1/agent-types/seed-builtin")
    agent_type = (await client.get("/api/v1/agent-types/coding")).json()

    create_resp = await client.post("/api/v1/agents", json={
        "workspace_id": ws["id"], "agent_type_id": agent_type["id"], "name": "Coder", "owner_id": "u1",
    })
    assert create_resp.status_code == 201
    agent = create_resp.json()
    assert agent["status"] == "draft"

    activate_resp = await client.post(f"/api/v1/agents/{agent['id']}/activate")
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "active"

    grant_resp = await client.post(f"/api/v1/agents/{agent['id']}/tool-permissions", json={
        "tool_name": "calculator", "level": "execute", "granted_by": "u1",
    })
    assert grant_resp.status_code == 201

    perms_resp = await client.get(f"/api/v1/agents/{agent['id']}/tool-permissions")
    # the coding agent type grants its own default tool permissions at creation time,
    # so "calculator" is additive on top of those, not the only grant.
    tool_names = {p["tool_name"] for p in perms_resp.json()}
    assert "calculator" in tool_names

    search_resp = await client.get("/api/v1/agents/search", params={"workspace_id": ws["id"], "q": "coder"})
    assert len(search_resp.json()) == 1
