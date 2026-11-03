"""API-level test of the full prompt lifecycle: create -> version -> promote
gated by evaluation score -> render. Exercises the router, service, domain
aggregate, and repository together — the "integration across layers" test
that unit tests deliberately don't cover.
"""

import pytest


@pytest.mark.asyncio
async def test_prompt_lifecycle(client, auth_headers):
    r = await client.post(
        "/api/v1/workspaces",
        json={"organization_id": "org-x", "name": "WS for prompts"},
        headers=auth_headers,
    )
    workspace_id = r.json()["id"]

    r = await client.post(
        "/api/v1/prompts",
        json={"workspace_id": workspace_id, "name": "Test Prompt", "target_model": "claude-haiku-4.5"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    prompt_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/prompts/{prompt_id}/versions", json={"content": "Hi {{name}}"}, headers=auth_headers
    )
    assert r.status_code == 201
    assert r.json()["version"] == 1

    # Member role lacks prompt:promote — must be forbidden.
    r = await client.post(
        f"/api/v1/prompts/{prompt_id}/versions/1/promote",
        json={"target_status": "staged"},
        headers=auth_headers,
    )
    assert r.status_code == 403

    r = await client.post(
        f"/api/v1/prompts/{prompt_id}/render", json={"variables": {"name": "Mohhet"}}, headers=auth_headers
    )
    assert r.status_code == 200
    assert "Mohhet" in r.json()["rendered"]


@pytest.mark.asyncio
async def test_prompt_not_found_returns_404(client, auth_headers):
    r = await client.get("/api/v1/prompts/does-not-exist", headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
