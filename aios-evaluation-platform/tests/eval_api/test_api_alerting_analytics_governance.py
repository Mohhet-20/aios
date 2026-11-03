import pytest


@pytest.mark.asyncio
async def test_alerting_rule_and_incident_lifecycle(client):
    ws = await client.post("/api/v1/workspaces", json={"name": "Alert Co", "slug": "alert-co-api", "organization_id": "org-1"})
    workspace_id = ws.json()["id"]

    rule_resp = await client.post("/api/v1/alerting/rules", json={
        "workspace_id": workspace_id, "name": "High Latency", "category": "latency", "severity": "warning",
        "condition": {"metric": "latency_ms", "comparator": "gt", "threshold": 1000},
    })
    assert rule_resp.status_code == 201
    rule = rule_resp.json()

    eval_resp = await client.post(f"/api/v1/alerting/rules/{rule['id']}/evaluate", params={"observed_value": 5000})
    assert eval_resp.status_code == 200
    alert = eval_resp.json()
    assert alert["status"] == "open"

    ack_resp = await client.post(f"/api/v1/alerting/alerts/{alert['id']}/acknowledge", params={"by": "u1"})
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"

    resolve_resp = await client.post(f"/api/v1/alerting/alerts/{alert['id']}/resolve", params={"by": "u1"})
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"

    trigger_resp = await client.post("/api/v1/alerting/alerts", json={
        "workspace_id": workspace_id, "category": "cost", "severity": "critical", "message": "Cost spiked",
    })
    assert trigger_resp.status_code == 201

    list_resp = await client.get("/api/v1/alerting/alerts", params={"workspace_id": workspace_id})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2


@pytest.mark.asyncio
async def test_analytics_snapshot_and_recommendation(client):
    ws = await client.post("/api/v1/workspaces", json={"name": "Analytics Co", "slug": "analytics-co-api", "organization_id": "org-1"})
    workspace_id = ws.json()["id"]

    snapshot_resp = await client.post("/api/v1/analytics/snapshots/quality", params={
        "workspace_id": workspace_id, "period_start": "2020-01-01T00:00:00Z", "period_end": "2030-01-01T00:00:00Z",
    })
    assert snapshot_resp.status_code == 200
    assert snapshot_resp.json()["data"]["run_count"] == 0

    list_resp = await client.get("/api/v1/analytics/snapshots", params={"workspace_id": workspace_id})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    rec_resp = await client.post("/api/v1/analytics/recommendations", json={
        "workspace_id": workspace_id, "category": "cost_optimization", "target_type": "evaluation", "title": "Cut spend",
        "description": "desc", "evidence": {"a": 1},
    })
    assert rec_resp.status_code == 201
    recommendation = rec_resp.json()

    accept_resp = await client.post(f"/api/v1/analytics/recommendations/{recommendation['id']}/accept")
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_governance_rbac_and_audit_and_retention(client):
    grant_resp = await client.post("/api/v1/governance/grants", json={
        "principal_id": "user-1", "resource_type": "workspace", "resource_id": "ws-1", "role": "analyst", "granted_by": "owner-1",
    })
    assert grant_resp.status_code == 201

    role_resp = await client.get("/api/v1/governance/grants/effective-role", params={
        "principal_id": "user-1", "resource_type": "workspace", "resource_id": "ws-1",
    })
    assert role_resp.status_code == 200
    assert role_resp.json()["role"] == "analyst"

    revoke_resp = await client.post("/api/v1/governance/grants/revoke", params={
        "principal_id": "user-1", "resource_type": "workspace", "resource_id": "ws-1",
    })
    assert revoke_resp.status_code == 200

    role_after = await client.get("/api/v1/governance/grants/effective-role", params={
        "principal_id": "user-1", "resource_type": "workspace", "resource_id": "ws-1",
    })
    assert role_after.json()["role"] is None

    audit_resp = await client.get("/api/v1/governance/audit-log/actor", params={"actor_id": "user-1"})
    assert audit_resp.status_code == 200

    sweep_resp = await client.post("/api/v1/governance/retention/sweep-observability-events")
    assert sweep_resp.status_code == 200
    assert sweep_resp.json()["removed"] == 0
