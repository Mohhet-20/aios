import pytest


async def _make_workspace(client, name="Sched Co", slug="sched-co"):
    r = await client.post("/api/v1/workspaces", json={"name": name, "slug": slug, "organization_id": "org-1"})
    assert r.status_code == 201
    return r.json()


async def _publish_tool(client, workspace_id, *, name="Tool", sensitivity_level="normal"):
    r = await client.post("/api/v1/tools", json={
        "workspace_id": workspace_id, "name": name, "owner_id": "u1", "category": "custom", "organization_id": "org-1",
    })
    tool = r.json()
    r = await client.post(f"/api/v1/tools/{tool['id']}/versions/draft", params={"created_by": "u1"})
    version = r.json()
    r = await client.patch(f"/api/v1/tools/{tool['id']}/versions/{version['id']}", json={
        "fields": {
            "connector_key": "echo", "default_max_retries": 0, "default_timeout_seconds": 10,
            "default_retry_backoff_seconds": 0.01, "sensitivity_level": sensitivity_level,
        },
    })
    r = await client.post(f"/api/v1/tools/{tool['id']}/versions/{version['id']}/publish")
    return tool, r.json()


@pytest.mark.asyncio
async def test_immediate_schedule_and_manual_tick(client):
    ws = await _make_workspace(client)
    tool, _version = await _publish_tool(client, ws["id"])

    r = await client.post("/api/v1/schedules/immediate", json={"tool_id": tool["id"], "workspace_id": ws["id"], "created_by": "u1"})
    assert r.status_code == 201, r.text
    schedule = r.json()
    assert schedule["status"] == "active"

    r = await client.post("/api/v1/schedules/tick")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["started_count"] == 1
    assert body["executions"][0]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_cron_schedule_pause_resume_cancel(client):
    ws = await _make_workspace(client, name="Sched Co 2", slug="sched-co-2")
    tool, _version = await _publish_tool(client, ws["id"], name="Tool 2")

    r = await client.post("/api/v1/schedules/cron", json={
        "tool_id": tool["id"], "workspace_id": ws["id"], "created_by": "u1", "cron_expression": "0 0 * * *",
    })
    assert r.status_code == 201, r.text
    schedule = r.json()

    r = await client.post(f"/api/v1/schedules/{schedule['id']}/pause")
    assert r.json()["status"] == "paused"

    r = await client.post(f"/api/v1/schedules/{schedule['id']}/resume")
    assert r.json()["status"] == "active"

    r = await client.post(f"/api/v1/schedules/{schedule['id']}/cancel")
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_rbac_grant_and_revoke(client):
    r = await client.post("/api/v1/governance/grants", json={
        "principal_id": "user-1", "resource_type": "workspace", "resource_id": "ws-1", "role": "operator", "granted_by": "admin-1",
    })
    assert r.status_code == 201, r.text
    grant = r.json()

    r = await client.get("/api/v1/governance/grants", params={"principal_id": "user-1"})
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.post(f"/api/v1/governance/grants/{grant['id']}/revoke")
    assert r.status_code == 200
    assert r.json()["revoked_at"] is not None


@pytest.mark.asyncio
async def test_sensitive_tool_requires_approval_via_api(client):
    ws = await _make_workspace(client, name="Sched Co 3", slug="sched-co-3")
    tool, _version = await _publish_tool(client, ws["id"], name="Sensitive Tool", sensitivity_level="critical")

    r = await client.post("/api/v1/executions", json={"tool_id": tool["id"], "input_data": {}})
    assert r.status_code == 403, r.text

    r = await client.post("/api/v1/governance/approvals", json={
        "resource_type": "tool", "resource_id": tool["id"], "requested_by": "u1", "sensitivity_level": "critical",
    })
    assert r.status_code == 201, r.text
    gate = r.json()

    r = await client.post(f"/api/v1/governance/approvals/{gate['id']}/approve", json={"approver_id": "admin-1"})
    assert r.status_code == 200, r.text

    r = await client.post("/api/v1/executions", json={"tool_id": tool["id"], "input_data": {}, "approval_gate_id": gate["id"]})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "succeeded"

    r = await client.get("/api/v1/governance/audit-log", params={"resource_type": "tool", "resource_id": tool["id"]})
    assert r.status_code == 200
    assert any(entry["action"] == "tool.execute" for entry in r.json())
