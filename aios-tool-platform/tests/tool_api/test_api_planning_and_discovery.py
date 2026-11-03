import pytest


async def _make_workspace(client, name="Plan Co", slug="plan-co"):
    r = await client.post("/api/v1/workspaces", json={"name": name, "slug": slug, "organization_id": "org-1"})
    assert r.status_code == 201
    return r.json()


async def _publish_tool(client, workspace_id, *, name, capabilities, description=""):
    r = await client.post("/api/v1/tools", json={
        "workspace_id": workspace_id, "name": name, "owner_id": "u1", "category": "custom",
        "organization_id": "org-1", "description": description,
    })
    tool = r.json()
    r = await client.post(f"/api/v1/tools/{tool['id']}/versions/draft", params={"created_by": "u1"})
    version = r.json()
    r = await client.patch(f"/api/v1/tools/{tool['id']}/versions/{version['id']}", json={
        "fields": {"connector_key": "echo", "capabilities": capabilities, "default_max_retries": 0},
    })
    r = await client.post(f"/api/v1/tools/{tool['id']}/versions/{version['id']}/publish")
    return tool, r.json()


@pytest.mark.asyncio
async def test_planning_select_tool_and_build_plan(client):
    ws = await _make_workspace(client)
    await _publish_tool(client, ws["id"], name="GitHub Issue Creator", capabilities=["create_issue"], description="creates github issues")
    await _publish_tool(client, ws["id"], name="Slack Notifier", capabilities=["send_message"], description="sends slack messages")

    r = await client.post("/api/v1/planning/select-tool", json={"workspace_id": ws["id"], "query": "create a github issue"})
    assert r.status_code == 200, r.text
    ranked = r.json()
    assert ranked[0]["name"] == "GitHub Issue Creator"

    r = await client.post("/api/v1/planning/build-plan", json={"steps": [["step1", "tool-1", {"q": "hello"}]]})
    assert r.status_code == 200, r.text
    assert len(r.json()["steps"]) == 1


@pytest.mark.asyncio
async def test_discovery_favorites_and_recommendations(client):
    ws = await _make_workspace(client, name="Plan Co 2", slug="plan-co-2")
    tool, _version = await _publish_tool(client, ws["id"], name="Fav Tool", capabilities=["x"])

    r = await client.post(f"/api/v1/registry/favorites/{tool['id']}")
    assert r.status_code == 201, r.text

    r = await client.get("/api/v1/registry/favorites")
    assert r.status_code == 200
    assert any(t["id"] == tool["id"] for t in r.json())

    r = await client.delete(f"/api/v1/registry/favorites/{tool['id']}")
    assert r.status_code == 204

    r = await client.get("/api/v1/registry/favorites")
    assert r.json() == []
