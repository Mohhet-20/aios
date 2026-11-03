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
async def test_workspace_project_prompt_version_flow(client):
    ws_resp = await client.post("/api/v1/workspaces", json={"name": "WS", "slug": "ws-api", "organization_id": "org1"})
    assert ws_resp.status_code == 201
    ws = ws_resp.json()

    proj_resp = await client.post(f"/api/v1/workspaces/{ws['id']}/projects", json={"name": "Proj", "slug": "proj-api"})
    assert proj_resp.status_code == 201
    proj = proj_resp.json()

    prompt_resp = await client.post("/api/v1/prompts", json={"workspace_id": ws["id"], "project_id": proj["id"], "name": "QA Prompt"})
    assert prompt_resp.status_code == 201
    prompt = prompt_resp.json()
    assert prompt["owner_id"] == "u1"

    version_resp = await client.post(f"/api/v1/prompts/{prompt['id']}/versions", json={"user_template": "Answer {{q}}."})
    assert version_resp.status_code == 201
    version = version_resp.json()
    assert version["version_number"] == 1

    submit_resp = await client.post(f"/api/v1/prompts/{prompt['id']}/versions/{version['id']}/submit-for-review")
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "in_review"

    approve_resp = await client.post(f"/api/v1/prompts/{prompt['id']}/versions/{version['id']}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    promote_resp = await client.post(
        f"/api/v1/prompts/{prompt['id']}/versions/{version['id']}/promote", json={"target_branch": "stable"}
    )
    assert promote_resp.status_code == 200
    assert promote_resp.json()["branch"] == "stable"

    list_resp = await client.get(f"/api/v1/prompts/{prompt['id']}/versions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_prompt_resp = await client.get(f"/api/v1/prompts/{prompt['id']}")
    assert get_prompt_resp.status_code == 200


@pytest.mark.asyncio
async def test_prompt_not_found_returns_404(client):
    resp = await client.get("/api/v1/prompts/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


@pytest.mark.asyncio
async def test_missing_actor_header_returns_401(app):
    import httpx
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as anon_client:
        resp = await anon_client.post("/api/v1/prompts", json={"workspace_id": "w", "project_id": "p", "name": "N"})
    assert resp.status_code == 401
