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
async def test_workspace_and_evaluation_lifecycle(client):
    ws = await client.post("/api/v1/workspaces", json={"name": "API Co", "slug": "api-co", "organization_id": "org-1"})
    assert ws.status_code == 201
    workspace_id = ws.json()["id"]

    fetched = await client.get(f"/api/v1/workspaces/{workspace_id}")
    assert fetched.status_code == 200

    listed = await client.get("/api/v1/workspaces", params={"organization_id": "org-1"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    create_eval = await client.post("/api/v1/evaluations", json={
        "workspace_id": workspace_id, "organization_id": "org-1", "name": "API Eval", "owner_id": "u1", "category": "prompt",
    })
    assert create_eval.status_code == 201
    evaluation = create_eval.json()
    assert evaluation["status"] == "draft"

    get_resp = await client.get(f"/api/v1/evaluations/{evaluation['id']}")
    assert get_resp.status_code == 200

    list_resp = await client.get("/api/v1/evaluations", params={"workspace_id": workspace_id})
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    search_resp = await client.get("/api/v1/evaluations/search", params={"workspace_id": workspace_id, "q": "API"})
    assert search_resp.status_code == 200
    assert len(search_resp.json()) == 1

    update_resp = await client.patch(f"/api/v1/evaluations/{evaluation['id']}", json={"description": "updated"})
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "updated"

    draft_resp = await client.post(f"/api/v1/evaluations/{evaluation['id']}/versions/draft", params={"created_by": "u1"})
    assert draft_resp.status_code == 200
    version = draft_resp.json()

    patch_resp = await client.patch(f"/api/v1/evaluations/versions/{version['id']}", json={
        "metric_keys": ["accuracy"], "target_config": {"type": "prompt", "static_response": "2"}, "pass_threshold": 1.0,
    })
    assert patch_resp.status_code == 200

    publish_resp = await client.post(f"/api/v1/evaluations/versions/{version['id']}/publish")
    assert publish_resp.status_code == 200
    assert publish_resp.json()["status"] == "published"

    active_eval = await client.get(f"/api/v1/evaluations/{evaluation['id']}")
    assert active_eval.json()["status"] == "active"

    deprecate_resp = await client.post(f"/api/v1/evaluations/{evaluation['id']}/deprecate")
    assert deprecate_resp.status_code == 200
    assert deprecate_resp.json()["status"] == "deprecated"

    archive_resp = await client.post(f"/api/v1/evaluations/{evaluation['id']}/archive")
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "archived"

    delete_resp = await client.delete(f"/api/v1/evaluations/{evaluation['id']}")
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_get_missing_evaluation_returns_404(client):
    resp = await client.get("/api/v1/evaluations/does-not-exist")
    assert resp.status_code == 404
