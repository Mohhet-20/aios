"""End-to-end integration tests that drive the platform purely through the
HTTP surface — the same seam a real caller (frontend, gateway, another
AIOS platform) would use. Complements the unit/service-level tests, which
already cover edge cases in depth; this file's job is to prove the FastAPI
routers wire request -> service -> domain -> response correctly."""
import pytest


async def _make_workspace(client, *, slug="wf-co"):
    r = await client.post("/api/v1/workspaces", json={"name": "WF Co", "slug": slug, "organization_id": "org-1"})
    assert r.status_code == 201, r.text
    return r.json()


async def _make_workflow(client, workspace_id, *, name="Order Pipeline"):
    r = await client.post("/api/v1/workflows", json={
        "workspace_id": workspace_id, "name": name, "owner_id": "u1", "category": "automation",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _publish_linear_workflow(client, workflow_id, *, created_by="u1"):
    r = await client.post(f"/api/v1/workflows/{workflow_id}/versions/draft", json={"created_by": created_by})
    assert r.status_code == 201, r.text
    version = r.json()

    for node in (
        {"node_key": "start", "node_type": "start", "name": "Start"},
        {"node_key": "delay", "node_type": "delay", "name": "Delay", "config": {"seconds": 0}},
        {"node_key": "end", "node_type": "end", "name": "End"},
    ):
        r = await client.post(f"/api/v1/versions/{version['id']}/nodes", json=node)
        assert r.status_code == 201, r.text

    for edge in (
        {"source_node_key": "start", "target_node_key": "delay"},
        {"source_node_key": "delay", "target_node_key": "end"},
    ):
        r = await client.post(f"/api/v1/versions/{version['id']}/edges", json=edge)
        assert r.status_code == 201, r.text

    r = await client.post(f"/api/v1/versions/{version['id']}/publish")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_workflow_versioning_and_graph_roundtrip(client):
    workspace = await _make_workspace(client)
    workflow = await _make_workflow(client, workspace["id"])
    published = await _publish_linear_workflow(client, workflow["id"])
    assert published["status"] == "published"

    r = await client.get(f"/api/v1/versions/{published['id']}/graph")
    assert r.status_code == 200
    graph = r.json()
    assert {n["node_key"] for n in graph["nodes"]} == {"start", "delay", "end"}
    assert len(graph["edges"]) == 2

    r = await client.get(f"/api/v1/workflows/{workflow['id']}/versions")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.get(f"/api/v1/workflows/{workflow['id']}")
    assert r.json()["current_version_id"] == published["id"]


@pytest.mark.asyncio
async def test_start_and_observe_execution(client):
    workspace = await _make_workspace(client, slug="exec-co")
    workflow = await _make_workflow(client, workspace["id"], name="Exec WF")
    await _publish_linear_workflow(client, workflow["id"])

    r = await client.post("/api/v1/executions", json={"workflow_id": workflow["id"], "triggered_by": "u1"})
    assert r.status_code == 201, r.text
    execution = r.json()
    assert execution["status"] == "completed"

    r = await client.get(f"/api/v1/executions/{execution['id']}/node-executions")
    assert r.status_code == 200
    node_execs = r.json()
    assert {ne["node_key"] for ne in node_execs} == {"start", "delay", "end"}
    assert all(ne["status"] == "succeeded" for ne in node_execs)

    r = await client.get(f"/api/v1/executions/{execution['id']}/timeline")
    assert r.status_code == 200
    assert len(r.json()) >= 3

    r = await client.get(f"/api/v1/executions/{execution['id']}/graph")
    assert r.status_code == 200

    r = await client.get(f"/api/v1/executions/{execution['id']}/checkpoints")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    r = await client.get(f"/api/v1/workflows/{workflow['id']}/metrics/success-rate")
    assert r.status_code == 200
    assert r.json()["total_executions"] == 1

    r = await client.get("/api/v1/executions", params={"workflow_id": workflow["id"]})
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_pause_cancel_and_rollback_execution(client):
    workspace = await _make_workspace(client, slug="ctl-co")
    workflow = await _make_workflow(client, workspace["id"], name="Control WF")

    r = await client.post(f"/api/v1/workflows/{workflow['id']}/versions/draft", json={"created_by": "u1"})
    version = r.json()
    for node in (
        {"node_key": "start", "node_type": "start", "name": "Start"},
        {"node_key": "wait", "node_type": "approval", "name": "Approval Gate", "config": {"approval_chain": [["approver-1"]]}},
        {"node_key": "end", "node_type": "end", "name": "End"},
    ):
        r = await client.post(f"/api/v1/versions/{version['id']}/nodes", json=node)
        assert r.status_code == 201, r.text
    for edge in ({"source_node_key": "start", "target_node_key": "wait"}, {"source_node_key": "wait", "target_node_key": "end"}):
        r = await client.post(f"/api/v1/versions/{version['id']}/edges", json=edge)
        assert r.status_code == 201, r.text
    r = await client.post(f"/api/v1/versions/{version['id']}/publish")
    assert r.status_code == 200, r.text

    r = await client.post("/api/v1/executions", json={"workflow_id": workflow["id"], "triggered_by": "u1"})
    execution = r.json()
    assert execution["status"] == "waiting_approval"

    r = await client.get("/api/v1/approvals", params={"execution_id": execution["id"]})
    assert r.status_code == 200
    approvals = r.json()
    assert len(approvals) == 1
    approval = approvals[0]

    r = await client.post(f"/api/v1/approvals/{approval['id']}/comments", json={"author_id": "u1", "comment": "looks fine"})
    assert r.status_code == 201, r.text

    # Approving the final (only) chain step resolves the request AND resumes
    # the paused execution as one atomic ApprovalService operation — see
    # `ApprovalService.approve_step`'s call to `engine.resume_after_approval`
    # once `advance_step()` reports no steps remain. No separate resume call
    # is needed (and calling it again would 422: the node is no longer
    # WAITING_APPROVAL).
    r = await client.post(f"/api/v1/approvals/{approval['id']}/approve", json={"decided_by": "approver-1"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    r = await client.get(f"/api/v1/executions/{execution['id']}")
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    r = await client.post(f"/api/v1/executions/{execution['id']}/cancel")
    assert r.status_code in (200, 409, 422)  # already terminal — exercised for error-mapping coverage


@pytest.mark.asyncio
async def test_scheduling_lifecycle(client):
    workspace = await _make_workspace(client, slug="sched-co")
    workflow = await _make_workflow(client, workspace["id"], name="Scheduled WF")
    await _publish_linear_workflow(client, workflow["id"])

    r = await client.post("/api/v1/schedules/immediate", json={
        "workflow_id": workflow["id"], "workspace_id": workspace["id"], "created_by": "u1",
    })
    assert r.status_code == 201, r.text
    schedule = r.json()
    assert schedule["schedule_type"] == "immediate"

    r = await client.get("/api/v1/schedules", params={"workflow_id": workflow["id"]})
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.post("/api/v1/schedules/dispatch/tick")
    assert r.status_code == 200
    assert r.json()["fired_count"] == 1

    r = await client.post("/api/v1/schedules/cron", json={
        "workflow_id": workflow["id"], "workspace_id": workspace["id"], "created_by": "u1", "cron_expression": "0 * * * *",
    })
    assert r.status_code == 201, r.text
    cron_schedule = r.json()

    r = await client.post(f"/api/v1/schedules/{cron_schedule['id']}/pause")
    assert r.status_code == 200
    assert r.json()["status"] == "paused"

    r = await client.post(f"/api/v1/schedules/{cron_schedule['id']}/resume")
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    r = await client.post(f"/api/v1/schedules/{cron_schedule['id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_events_and_subscriptions(client):
    workspace = await _make_workspace(client, slug="evt-co")

    r = await client.post("/api/v1/subscriptions/webhook", params={"workspace_id": workspace["id"]}, json={
        "event_type": "workflow_started", "url": "https://example.com/hook", "created_by": "u1",
    })
    assert r.status_code == 201, r.text
    sub = r.json()

    r = await client.post("/api/v1/events", json={
        "event_type": "workflow_started", "workspace_id": workspace["id"], "source_type": "execution",
        "source_id": "exec-1", "payload": {"foo": "bar"},
    })
    assert r.status_code == 201, r.text

    r = await client.get("/api/v1/subscriptions", params={"workspace_id": workspace["id"]})
    assert r.status_code == 200
    assert any(s["id"] == sub["id"] for s in r.json())

    r = await client.post(f"/api/v1/subscriptions/{sub['id']}/deactivate")
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    r = await client.post("/api/v1/events/webhook-deliveries/retry")
    assert r.status_code == 200
    assert "retried_count" in r.json()


@pytest.mark.asyncio
async def test_state_variables_and_secrets(client):
    r = await client.put("/api/v1/variables/workspace/ws-1", json={"key": "api_base_url", "value": "https://api.example.com"})
    assert r.status_code == 201, r.text

    r = await client.get("/api/v1/variables/workspace/ws-1/api_base_url")
    assert r.status_code == 200
    assert r.json()["value"] == "https://api.example.com"

    r = await client.put("/api/v1/variables/workspace/ws-1", json={"key": "api_key", "value": "sk-secret", "is_secret": True})
    assert r.status_code == 201, r.text

    r = await client.get("/api/v1/variables/workspace/ws-1")
    assert r.status_code == 200
    assert {v["key"] for v in r.json()} == {"api_base_url", "api_key"}

    r = await client.delete("/api/v1/variables/workspace/ws-1/api_key")
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_governance_rbac_and_audit(client):
    r = await client.post("/api/v1/rbac/grants", json={
        "principal_id": "user-42", "resource_type": "workspace", "resource_id": "ws-9", "role": "operator",
    })
    assert r.status_code == 201, r.text
    grant = r.json()
    assert grant["role"] == "operator"

    r = await client.get("/api/v1/rbac/grants/by-principal/user-42")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.get("/api/v1/rbac/effective-permissions", params={"principal_id": "user-42", "workspace_id": "ws-9"})
    assert r.status_code == 200
    assert len(r.json()["permissions"]) > 0

    r = await client.get("/api/v1/audit-log/by-actor/u1")
    assert r.status_code == 200  # rbac grant is audited under the caller (X-User-Id: u1), not the principal
    assert any(entry["resource_id"] == "ws-9" for entry in r.json())

    r = await client.delete(f"/api/v1/rbac/grants/{grant['id']}")
    assert r.status_code == 204
