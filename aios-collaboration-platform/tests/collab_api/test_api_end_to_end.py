"""Drives the platform purely through HTTP (`httpx.AsyncClient` against
the real FastAPI app), exercising the full collaboration lifecycle
across nearly every router: workspace -> project -> asset -> comment
-> reaction -> version -> review -> approval -> notification -> search
-> library -> share link -> audit log -> observability. Complements
the service-level unit tests (which already cover edge cases and
guarded transitions in depth) by proving the routers/dependency wiring
/exception-handler mapping actually works end to end."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_full_collaboration_lifecycle_over_http(client):
    ws_resp = await client.post("/api/v1/workspaces", json={"name": "API Flow WS", "owner_id": "user-1"})
    assert ws_resp.status_code == 201
    workspace_id = ws_resp.json()["id"]

    member_resp = await client.post(f"/api/v1/workspaces/{workspace_id}/members", json={"user_id": "user-2", "role": "editor"})
    assert member_resp.status_code == 201

    project_resp = await client.post("/api/v1/projects", json={"workspace_id": workspace_id, "name": "Launch"})
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    asset_resp = await client.post("/api/v1/assets", json={
        "workspace_id": workspace_id, "project_id": project_id, "asset_type": "prompt",
        "external_ref_id": "prompt-api-1", "name": "Welcome Prompt", "owner_id": "user-1",
    })
    assert asset_resp.status_code == 201
    asset_id = asset_resp.json()["id"]

    comment_resp = await client.post("/api/v1/comments", json={"asset_id": asset_id, "author_id": "user-2", "body": "Looks great!"})
    assert comment_resp.status_code == 201
    comment_id = comment_resp.json()["id"]

    reaction_resp = await client.post(f"/api/v1/comments/{comment_id}/reactions", json={"user_id": "user-1", "emoji": "🎉"})
    assert reaction_resp.status_code == 201

    resolve_resp = await client.post(f"/api/v1/comments/{comment_id}/resolve", params={"resolved_by": "user-1"})
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["is_resolved"] is True

    version_resp = await client.post("/api/v1/versions", json={
        "asset_id": asset_id, "created_by": "user-1", "content_snapshot": {"text": "Welcome!"},
    })
    assert version_resp.status_code == 201
    version_id = version_resp.json()["id"]
    assert version_resp.json()["version_number"] == 1

    review_resp = await client.post("/api/v1/reviews", json={
        "asset_id": asset_id, "requested_by": "user-1", "reviewer_ids": ["user-2"], "version_id": version_id,
    })
    assert review_resp.status_code == 201
    review_id = review_resp.json()["id"]

    approve_resp = await client.post(f"/api/v1/reviews/{review_id}/approve", json={"reviewer_id": "user-2"})
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    notify_resp = await client.post("/api/v1/notifications", json={
        "recipient_id": "user-1", "notification_type": "approval_decision", "title": "Your review request was approved",
    })
    assert notify_resp.status_code == 201
    unread_resp = await client.get("/api/v1/notifications/user/user-1/unread-count")
    assert unread_resp.json()["unread_count"] == 1

    search_resp = await client.get("/api/v1/search", params={"q": "welcome", "workspace_id": workspace_id})
    assert search_resp.status_code == 200
    assert len(search_resp.json()) == 1

    publish_resp = await client.post("/api/v1/libraries/publish", json={
        "asset_id": asset_id, "library_type": "prompt", "published_by": "user-1", "visibility": "organization",
    })
    assert publish_resp.status_code == 201
    library_asset_id = publish_resp.json()["id"]
    install_resp = await client.post(f"/api/v1/libraries/{library_asset_id}/install")
    assert install_resp.status_code == 200
    assert install_resp.json()["install_count"] == 1

    share_resp = await client.post(f"/api/v1/governance/assets/{asset_id}/share-links", json={"created_by": "user-1"})
    assert share_resp.status_code == 201
    assert "token" in share_resp.json()

    activity_resp = await client.get(f"/api/v1/activity/workspace/{workspace_id}")
    assert activity_resp.status_code == 200

    usage_resp = await client.get(f"/api/v1/observability/workspace/{workspace_id}/usage")
    assert usage_resp.status_code == 200
    assert usage_resp.json()["asset_count"] == 1
    assert usage_resp.json()["member_count"] == 2


async def test_not_found_maps_to_404(client):
    resp = await client.get("/api/v1/workspaces/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


async def test_conflict_maps_to_409(client):
    ws_resp = await client.post("/api/v1/workspaces", json={"name": "Dup WS", "owner_id": "user-1", "slug": "dup-api-slug"})
    assert ws_resp.status_code == 201
    dup_resp = await client.post("/api/v1/workspaces", json={"name": "Other", "owner_id": "user-2", "slug": "dup-api-slug"})
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"] == "ConflictError"


async def test_permission_denied_maps_to_403(client):
    ws_resp = await client.post("/api/v1/workspaces", json={"name": "Perm WS", "owner_id": "user-1"})
    workspace_id = ws_resp.json()["id"]
    asset_resp = await client.post("/api/v1/assets", json={
        "workspace_id": workspace_id, "asset_type": "document", "external_ref_id": "doc-1", "name": "Doc", "owner_id": "user-1",
    })
    asset_id = asset_resp.json()["id"]
    comment_resp = await client.post("/api/v1/comments", json={"asset_id": asset_id, "author_id": "user-1", "body": "mine"})
    comment_id = comment_resp.json()["id"]

    edit_resp = await client.put(f"/api/v1/comments/{comment_id}", json={"editor_id": "user-intruder", "new_body": "hijacked"})
    assert edit_resp.status_code == 403
    assert edit_resp.json()["error"] == "PermissionDeniedError"


async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_health_liveness_probe(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


async def test_health_readiness_probe(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["components"][0]["name"] == "database"
    assert body["components"][0]["healthy"] is True
