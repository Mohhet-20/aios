import pytest


async def _make_workspace(client, name="Exec Co", slug="exec-co"):
    r = await client.post("/api/v1/workspaces", json={"name": name, "slug": slug, "organization_id": "org-1"})
    assert r.status_code == 201
    return r.json()


async def _publish_echo_tool(client, workspace_id, *, name="Echo Tool"):
    r = await client.post("/api/v1/tools", json={
        "workspace_id": workspace_id, "name": name, "owner_id": "u1", "category": "custom", "organization_id": "org-1",
    })
    assert r.status_code == 201, r.text
    tool = r.json()

    r = await client.post(f"/api/v1/tools/{tool['id']}/versions/draft", params={"created_by": "u1"})
    assert r.status_code == 201, r.text
    version = r.json()

    r = await client.patch(f"/api/v1/tools/{tool['id']}/versions/{version['id']}", json={
        "fields": {"connector_key": "echo", "default_max_retries": 0, "default_timeout_seconds": 10, "default_retry_backoff_seconds": 0.01},
    })
    assert r.status_code == 200, r.text

    r = await client.post(f"/api/v1/tools/{tool['id']}/versions/{version['id']}/publish")
    assert r.status_code == 200, r.text
    return tool, r.json()


@pytest.mark.asyncio
async def test_tool_lifecycle_via_api(client):
    ws = await _make_workspace(client)
    tool, version = await _publish_echo_tool(client, ws["id"])
    assert version["status"] == "published"

    r = await client.get(f"/api/v1/tools/{tool['id']}")
    assert r.json()["status"] == "published"
    assert r.json()["current_version_id"] == version["id"]

    r = await client.post(f"/api/v1/tools/{tool['id']}/disable")
    assert r.status_code == 200
    assert r.json()["status"] == "disabled"

    r = await client.post(f"/api/v1/tools/{tool['id']}/enable")
    assert r.status_code == 200
    assert r.json()["status"] == "published"


@pytest.mark.asyncio
async def test_start_execution_end_to_end(client):
    ws = await _make_workspace(client, name="Exec Co 2", slug="exec-co-2")
    tool, _version = await _publish_echo_tool(client, ws["id"], name="Echo Tool 2")

    r = await client.post("/api/v1/executions", json={"tool_id": tool["id"], "input_data": {"hello": "world"}})
    assert r.status_code == 201, r.text
    execution = r.json()
    assert execution["status"] == "succeeded"
    assert execution["output_data"] == {"hello": "world"}

    r = await client.get(f"/api/v1/executions/{execution['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == execution["id"]

    r = await client.get("/api/v1/executions", params={"tool_id": tool["id"]})
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_batch_execution_via_api(client):
    ws = await _make_workspace(client, name="Exec Co 3", slug="exec-co-3")
    tool, _version = await _publish_echo_tool(client, ws["id"], name="Echo Tool 3")

    r = await client.post("/api/v1/executions/batch", json={
        "tool_id": tool["id"], "input_batches": [{"i": 1}, {"i": 2}, {"i": 3}],
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["children"]) == 3
    assert all(c["status"] == "succeeded" for c in body["children"])


@pytest.mark.asyncio
async def test_cancel_pending_execution_via_api(client, repos):
    from tool_platform.domain.enums import ExecutionStatus
    from tool_platform.models.execution import ToolExecutionModel

    ws = await _make_workspace(client, name="Exec Co 4", slug="exec-co-4")
    tool, version = await _publish_echo_tool(client, ws["id"], name="Echo Tool 4")

    execution = await repos.executions.add(ToolExecutionModel(
        tool_id=tool["id"], tool_version_id=version["id"], workspace_id=ws["id"], status=ExecutionStatus.PENDING.value,
    ))
    await repos.session.commit()

    r = await client.post(f"/api/v1/executions/{execution.id}/cancel")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_observability_endpoints_reflect_real_execution(client):
    ws = await _make_workspace(client, name="Exec Co 5", slug="exec-co-5")
    tool, _version = await _publish_echo_tool(client, ws["id"], name="Echo Tool 5")
    await client.post("/api/v1/executions", json={"tool_id": tool["id"], "input_data": {}})

    r = await client.get(f"/api/v1/observability/tools/{tool['id']}/success-rate")
    assert r.status_code == 200
    assert r.json()["succeeded"] == 1

    r = await client.get(f"/api/v1/observability/tools/{tool['id']}/latency")
    assert r.status_code == 200
    assert r.json()["sample_size"] == 1
