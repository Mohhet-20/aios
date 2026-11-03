"""Drives the platform purely through HTTP, end to end, across every
domain — the same style as every prior AIOS platform's API test suite.
Uses a dedicated tenant id (`api-e2e-tenant`, set in conftest.py's
`client` fixture) rather than the generic "t1" used throughout the
unit-level test suites, specifically to avoid the cross-test commit
leak documented in `tests/conftest.py` (this file exercises
`AlertEvaluationService.evaluate_rule`, one of the commit-spanning-lock
methods, over HTTP)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_probe(client):
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
async def test_logging_flow(client):
    resp = await client.post("/api/v1/logs", json={"service_name": "api", "level": "error", "message": "boom"})
    assert resp.status_code == 201
    resp = await client.get("/api/v1/logs/search", params={"level": "error"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_metrics_flow(client):
    resp = await client.post("/api/v1/metrics", json={"name": "e2e_latency_ms", "metric_type": "gauge", "value": 42.0})
    assert resp.status_code == 201
    resp = await client.get("/api/v1/metrics/e2e_latency_ms/latest")
    assert resp.status_code == 200
    assert resp.json()["value"] == 42.0
    resp = await client.get("/api/v1/metrics/e2e_latency_ms/aggregate")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


@pytest.mark.asyncio
async def test_tracing_flow(client):
    resp = await client.post(
        "/api/v1/traces/e2e-trace-1/spans",
        json={"span_id": "root", "service_name": "api", "operation_name": "handle_request"},
    )
    assert resp.status_code == 201
    resp = await client.post("/api/v1/traces/e2e-trace-1/spans/root/end", json={"status": "ok"})
    assert resp.status_code == 200
    resp = await client.post("/api/v1/traces/e2e-trace-1/finalize")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    resp = await client.get("/api/v1/traces/e2e-trace-1/tree")
    assert resp.status_code == 200
    assert resp.json()[0]["span_id"] == "root"


@pytest.mark.asyncio
async def test_component_and_health_flow(client):
    resp = await client.post("/api/v1/components", json={"name": "e2e-db", "component_type": "database"})
    assert resp.status_code == 201
    component_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/health/components/{component_id}/results", json={"status": "healthy"})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/health/components/{component_id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    resp = await client.get("/api/v1/health/overall")
    assert resp.status_code == 200
    assert resp.json()["overall_status"] == "healthy"


@pytest.mark.asyncio
async def test_alerting_flow(client):
    resp = await client.post("/api/v1/metrics", json={"name": "e2e_error_rate", "metric_type": "gauge", "value": 0.95})
    assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/alerts/rules",
        json={"name": "e2e-high-error-rate", "alert_type": "threshold", "metric_name": "e2e_error_rate", "condition": {"operator": "gt", "value": 0.5}},
    )
    assert resp.status_code == 201
    rule_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/alerts/evaluate/{rule_id}")
    assert resp.status_code == 200
    alert = resp.json()
    assert alert["status"] == "firing"

    resp = await client.post(f"/api/v1/alerts/{alert['id']}/acknowledge")
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"

    resp = await client.post(f"/api/v1/alerts/{alert['id']}/resolve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_incident_flow(client):
    resp = await client.post("/api/v1/incidents", json={"title": "E2E outage", "severity": "sev2"})
    assert resp.status_code == 201
    incident_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/incidents/{incident_id}/acknowledge")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/incidents/{incident_id}/resolve", json={"resolution_notes": "fixed"})
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/incidents/{incident_id}/close")
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/incidents/{incident_id}/timeline")
    assert resp.status_code == 200
    assert len(resp.json()) == 4  # created, acknowledged, resolved, closed


@pytest.mark.asyncio
async def test_capacity_flow(client):
    for v in [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0]:
        resp = await client.post("/api/v1/capacity/snapshots", json={"resource_type": "e2e_storage", "value": v})
        assert resp.status_code == 201

    resp = await client.post("/api/v1/capacity/e2e_storage/forecast", json={"horizon_days": 30})
    assert resp.status_code == 201
    assert resp.json()["method"] == "linear_trend"


@pytest.mark.asyncio
async def test_topology_flow(client):
    resp = await client.post("/api/v1/topology/nodes", json={"name": "e2e-api", "node_type": "service"})
    node_a = resp.json()["id"]
    resp = await client.post("/api/v1/topology/nodes", json={"name": "e2e-db", "node_type": "service"})
    node_b = resp.json()["id"]
    resp = await client.post("/api/v1/topology/edges", json={"source_node_id": node_a, "target_node_id": node_b, "edge_type": "service"})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/topology/{node_b}/downstream-impact")
    assert node_a in resp.json()["impacted_node_ids"]


@pytest.mark.asyncio
async def test_dashboard_flow(client):
    resp = await client.post("/api/v1/dashboards", json={"name": "E2E Ops", "dashboard_type": "operations"})
    assert resp.status_code == 201
    dashboard_id = resp.json()["id"]
    resp = await client.get(f"/api/v1/dashboards/{dashboard_id}/render")
    assert resp.status_code == 200
    assert resp.json()["dashboard_type"] == "operations"


@pytest.mark.asyncio
async def test_reporting_flow(client):
    resp = await client.post("/api/v1/reports/generate", json={"report_type": "usage"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_governance_flow(client):
    resp = await client.post("/api/v1/governance/grants", json={"principal_id": "e2e-user", "role": "admin"})
    assert resp.status_code == 201
    resp = await client.get("/api/v1/governance/effective-role", params={"principal_id": "e2e-user"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"

    resp = await client.post("/api/v1/governance/audit", json={"action": "e2e.test", "resource_type": "test"})
    assert resp.status_code == 201
    resp = await client.get("/api/v1/governance/audit")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
