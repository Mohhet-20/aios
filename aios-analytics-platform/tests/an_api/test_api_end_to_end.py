"""Drives the platform purely through HTTP, end to end, across every
domain — the same style as every other AIOS platform's API test
suite. Uses a dedicated tenant id (`api-e2e-tenant`, set in
conftest.py's `client` fixture) rather than the generic ids used
throughout the unit-level test suites, to keep this suite's state
isolated from those."""
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
async def test_warehouse_flow(client):
    resp = await client.post(
        "/api/v1/metrics",
        json={"key": "orders.created", "name": "Orders Created", "data_source": "workflows"},
    )
    assert resp.status_code == 201
    metric = resp.json()
    assert metric["key"] == "orders.created"

    resp = await client.get("/api/v1/metrics/orders.created")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await client.post(
        "/api/v1/metric-events", json={"metric_key": "orders.created", "data_source": "workflows", "value": 10.0},
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/metric-events/batch",
        json={"events": [
            {"metric_key": "orders.created", "data_source": "workflows", "value": 5.0},
            {"metric_key": "orders.created", "data_source": "workflows", "value": 7.0},
        ]},
    )
    assert resp.status_code == 201
    assert len(resp.json()) == 2

    resp = await client.get("/api/v1/metric-events", params={"metric_key": "orders.created"})
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_analytics_rollup_flow(client):
    await client.post("/api/v1/metrics", json={"key": "revenue.total", "name": "Revenue", "data_source": "organizations"})
    for v in (100.0, 200.0):
        await client.post("/api/v1/metric-events", json={"metric_key": "revenue.total", "data_source": "organizations", "value": v})

    start = "2020-01-01T00:00:00Z"
    end = "2030-01-01T00:00:00Z"
    resp = await client.post(
        "/api/v1/rollups",
        json={"metric_key": "revenue.total", "domain": "financial", "period": "daily", "period_start": start, "period_end": end},
    )
    assert resp.status_code == 201
    assert resp.json()["value"] == 300.0

    resp = await client.get("/api/v1/rollups", params={"metric_key": "revenue.total"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await client.post(
        "/api/v1/rollups/financial",
        json={"metric_key": "revenue.total", "period": "daily", "period_start": start, "period_end": end},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_kpi_flow(client):
    resp = await client.post(
        "/api/v1/kpis",
        json={"name": "Retention", "scope": "business", "metric_key": "users.retention", "target_value": 0.9, "threshold_warning": 0.7},
    )
    assert resp.status_code == 201
    kpi_id = resp.json()["id"]

    resp = await client.get("/api/v1/kpis")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/kpis/{kpi_id}/snapshots", json={"value": 0.95})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/kpis/{kpi_id}/snapshots")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/v1/kpis/{kpi_id}/trend")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/kpis/{kpi_id}/archive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"

    resp = await client.post(f"/api/v1/kpis/{kpi_id}/reactivate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_report_flow(client):
    resp = await client.post("/api/v1/report-definitions", json={"name": "Ops Digest", "report_type": "operational"})
    assert resp.status_code == 201
    definition_id = resp.json()["id"]

    resp = await client.get("/api/v1/report-definitions")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/report-definitions/scheduled")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/report-definitions/{definition_id}/runs")
    assert resp.status_code == 201
    run_id = resp.json()["id"]
    assert resp.json()["status"] == "queued"

    resp = await client.post(f"/api/v1/report-runs/{run_id}/generate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    resp = await client.get(f"/api/v1/report-definitions/{definition_id}/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(f"/api/v1/report-definitions/{definition_id}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"

    resp = await client.post(f"/api/v1/report-definitions/{definition_id}/activate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_forecast_flow(client):
    await client.post("/api/v1/metrics", json={"key": "orders.count", "name": "Orders", "data_source": "workflows"})
    periods = [
        ("2020-01-01T00:00:00Z", "2020-01-02T00:00:00Z"),
        ("2020-01-02T00:00:00Z", "2020-01-03T00:00:00Z"),
        ("2020-01-03T00:00:00Z", "2020-01-04T00:00:00Z"),
    ]
    for v, (period_start, period_end) in zip((10.0, 20.0, 30.0), periods):
        await client.post(
            "/api/v1/metric-events",
            json={"metric_key": "orders.count", "data_source": "workflows", "value": v, "occurred_at": period_start},
        )
        await client.post(
            "/api/v1/rollups",
            json={
                "metric_key": "orders.count", "domain": "business", "period": "daily",
                "period_start": period_start, "period_end": period_end,
            },
        )

    resp = await client.post(
        "/api/v1/forecasts", json={"forecast_type": "usage", "metric_key": "orders.count", "method": "linear_regression", "horizon_days": 3},
    )
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    resp = await client.get("/api/v1/forecasts")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/forecasts/{job_id}/run")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    resp = await client.get(f"/api/v1/forecasts/{job_id}")
    assert resp.status_code == 200
    return job_id, resp.json()


@pytest.mark.asyncio
async def test_recommendation_flow(client):
    resp = await client.post("/api/v1/recommendations", json={"category": "cost_optimization", "title": "Cut idle capacity"})
    assert resp.status_code == 201
    rec_id = resp.json()["id"]

    resp = await client.get("/api/v1/recommendations")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/recommendations/{rec_id}/accept")
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    resp = await client.post(f"/api/v1/recommendations/{rec_id}/implement")
    assert resp.status_code == 200
    assert resp.json()["status"] == "implemented"


@pytest.mark.asyncio
async def test_dashboard_flow(client):
    resp = await client.post("/api/v1/dashboards", json={"name": "Exec Overview"})
    assert resp.status_code == 201
    dashboard_id = resp.json()["id"]

    resp = await client.put(f"/api/v1/dashboards/{dashboard_id}/layout", json={"layout": {"columns": 2}})
    assert resp.status_code == 200
    assert resp.json()["layout"] == {"columns": 2}

    resp = await client.post(f"/api/v1/dashboards/{dashboard_id}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    resp = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/widgets",
        json={"visualization_type": "line_chart", "title": "Revenue"},
    )
    assert resp.status_code == 201
    widget_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/dashboards/{dashboard_id}/widgets")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(
        f"/api/v1/dashboards/{dashboard_id}/saved-views", json={"name": "My View", "filters": {"region": "us"}},
    )
    assert resp.status_code == 201
    view_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/dashboards/{dashboard_id}/saved-views")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.delete(f"/api/v1/dashboards/{dashboard_id}/saved-views/{view_id}")
    assert resp.status_code == 204

    resp = await client.delete(f"/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}")
    assert resp.status_code == 204

    resp = await client.post(f"/api/v1/dashboards/{dashboard_id}/archive")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/dashboards/{dashboard_id}/republish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


@pytest.mark.asyncio
async def test_security_flow(client):
    resp = await client.post("/api/v1/roles", json={"principal_id": "user-1", "role_level": "admin"})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/roles/user-1")
    assert resp.status_code == 200
    assert resp.json()["role_level"] == "admin"

    resp = await client.post("/api/v1/row-level-rules", json={"resource_type": "dashboards", "mode": "tenant_scoped"})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/row-level-rules/dashboards")
    assert resp.status_code == 200

    resp = await client.post(
        "/api/v1/column-level-rules",
        json={"resource_type": "kpis", "restricted_columns": ["target_value"], "allowed_roles": ["editor"]},
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/audit-log", json={"action_type": "view", "resource_type": "dashboard", "resource_id": "dash-1"},
    )
    assert resp.status_code == 201

    resp = await client.get("/api/v1/audit-log")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(
        "/api/v1/lineage/edges", json={"source_ref": "raw_event", "target_ref": "rollup.daily", "stage_type": "aggregate"},
    )
    assert resp.status_code == 201

    resp = await client.get("/api/v1/lineage/upstream", params={"ref": "rollup.daily"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get("/api/v1/lineage/downstream", params={"ref": "raw_event"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_observability_flow(client):
    resp = await client.post("/api/v1/usage-events", json={"event_type": "dashboard_view", "resource_id": "dash-1"})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/usage-events")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/usage-events/summary")
    assert resp.status_code == 200
    assert resp.json() == {"dashboard_view": 1}

    resp = await client.post("/api/v1/query-performance", json={"query_ref": "widget.q1", "duration_ms": 5000.0})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/query-performance/slow", params={"threshold_ms": 1000.0})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(
        "/api/v1/forecast-accuracy", json={"forecast_job_id": "job-x", "predicted_value": 100.0, "actual_value": 110.0},
    )
    assert resp.status_code == 201

    resp = await client.get("/api/v1/forecast-accuracy/job-x")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get("/api/v1/forecast-accuracy/job-x/average-error")
    assert resp.status_code == 200

    await client.post("/api/v1/recommendations", json={"category": "cost_optimization", "title": "X"})
    resp = await client.get("/api/v1/recommendation-analytics/acceptance-rate")
    assert resp.status_code == 200
    resp = await client.get("/api/v1/recommendation-analytics/outcome-breakdown")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_validation_error_maps_to_422(client):
    resp = await client.post("/api/v1/kpis", json={"name": "Bad", "scope": "not_a_scope", "metric_key": "x", "target_value": 1})
    assert resp.status_code == 422
    assert resp.json()["error"] == "ValidationError"


@pytest.mark.asyncio
async def test_not_found_maps_to_404(client):
    resp = await client.get("/api/v1/kpis/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_missing_tenant_header_is_400(app):
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", trust_env=False) as c:
        resp = await c.get("/api/v1/kpis")
    assert resp.status_code == 400
