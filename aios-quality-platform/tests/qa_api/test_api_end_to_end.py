"""Drives the platform purely through HTTP, end to end, across every
domain — the same style as every other AIOS platform's API test
suite. Uses a dedicated tenant id (`api-e2e-tenant`, set in
conftest.py's `client` fixture) rather than the generic ids used
throughout the unit-level test suites, to keep this suite's state
isolated from those."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


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



async def test_testing_flow(client):
    resp = await client.post("/api/v1/test-suites", json={"name": "api-suite", "test_type": "unit"})
    assert resp.status_code == 201
    suite = resp.json()

    resp = await client.post(f"/api/v1/test-suites/{suite['id']}/cases", json={"name": "case-1", "test_type": "unit"})
    assert resp.status_code == 201
    case = resp.json()

    resp = await client.post("/api/v1/test-runs", json={"suite_id": suite["id"]})
    assert resp.status_code == 201
    run = resp.json()
    assert run["status"] == "queued"

    resp = await client.post(f"/api/v1/test-runs/{run['id']}/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    resp = await client.post(f"/api/v1/test-runs/{run['id']}/results", json={"test_case_id": case["id"], "result": "passed"})
    assert resp.status_code == 201

    resp = await client.post(f"/api/v1/test-runs/{run['id']}/finish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["summary"]["passed"] == 1

    resp = await client.get(f"/api/v1/test-suites/{suite['id']}/runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_ai_quality_flow(client):
    resp = await client.post("/api/v1/ai-quality/baselines", json={
        "dimension": "groundedness", "subject_ref": "agent:api-1", "baseline_score": 100.0, "sample_size": 10,
    })
    assert resp.status_code == 201

    resp = await client.post("/api/v1/ai-quality/evaluations", json={
        "dimension": "groundedness", "subject_ref": "agent:api-1", "score": 80.0,
    })
    assert resp.status_code == 201

    resp = await client.post("/api/v1/ai-quality/regression-scans", json={"dimension": "groundedness", "subject_ref": "agent:api-1"})
    assert resp.status_code == 201
    scan = resp.json()

    resp = await client.post(f"/api/v1/ai-quality/regression-scans/{scan['id']}/run")
    assert resp.status_code == 200
    finished = resp.json()
    assert finished["status"] == "completed"
    assert finished["severity"] == "critical"


async def test_performance_flow(client):
    resp = await client.post("/api/v1/performance-runs", json={"performance_test_type": "load", "target_ref": "svc:api-1"})
    assert resp.status_code == 201
    run = resp.json()

    resp = await client.post(f"/api/v1/performance-runs/{run['id']}/start")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/performance-runs/{run['id']}/benchmarks", json={"metric_type": "cpu_utilization", "value": 95.0, "unit": "pct"})
    assert resp.status_code == 201

    resp = await client.post(f"/api/v1/performance-runs/{run['id']}/finish")
    assert resp.status_code == 200
    assert "cpu_bound" in resp.json()["result"]["bottlenecks"]


async def test_chaos_flow(client):
    resp = await client.post("/api/v1/chaos-experiments", json={
        "failure_type": "node_failure", "target_ref": "svc:api-2", "blast_radius_pct": 10.0,
    })
    assert resp.status_code == 201
    experiment = resp.json()

    resp = await client.post(f"/api/v1/chaos-experiments/{experiment['id']}/start")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/chaos-experiments/{experiment['id']}/finish", json={"recovered": True, "recovery_time_seconds": 3.5})
    assert resp.status_code == 200
    assert resp.json()["recovered"] is True


async def test_security_testing_flow(client):
    resp = await client.post("/api/v1/security-scans", json={"security_test_type": "authentication", "target_ref": "svc:api-3"})
    assert resp.status_code == 201
    scan = resp.json()

    resp = await client.post(f"/api/v1/security-scans/{scan['id']}/start")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/security-scans/{scan['id']}/findings", json={"severity": "critical", "title": "hardcoded secret"})
    assert resp.status_code == 201

    resp = await client.post(f"/api/v1/security-scans/{scan['id']}/finish")
    assert resp.status_code == 200
    assert resp.json()["result"]["blocks_gate"] is True


async def test_validation_flow(client):
    resp = await client.post("/api/v1/api-validation-runs", json={"validation_type": "schema", "target_ref": "api:api-1"})
    assert resp.status_code == 201
    assert resp.json()["outcome"] == "passed"

    resp = await client.post("/api/v1/workflow-validation-runs", json={"workflow_ref": "wf:api-1"})
    assert resp.status_code == 201
    run = resp.json()

    resp = await client.post(f"/api/v1/workflow-validation-runs/{run['id']}/start")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/workflow-validation-runs/{run['id']}/checks", json={"check": "logic", "passed": True})
    assert resp.status_code == 201

    resp = await client.post(f"/api/v1/workflow-validation-runs/{run['id']}/finish")
    assert resp.status_code == 200
    assert resp.json()["result"]["all_passed"] is True


async def test_reliability_flow(client):
    resp = await client.post("/api/v1/slos", json={"name": "api-slo-1", "service_ref": "svc:api-4", "target_pct": 99.0})
    assert resp.status_code == 201
    slo = resp.json()

    resp = await client.post("/api/v1/reliability-snapshots", json={"service_ref": "svc:api-4", "metric_type": "availability", "value": 99.99})
    assert resp.status_code == 201

    resp = await client.post(f"/api/v1/slos/{slo['id']}/evaluate", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "meeting"


async def test_quality_gates_flow(client):
    resp = await client.post("/api/v1/coverage-snapshots", json={"subject_ref": "repo:api-1", "coverage_type": "code", "covered_pct": 90.0})
    assert resp.status_code == 201

    resp = await client.post("/api/v1/quality-gates", json={"name": "api-gate-1", "release_ref": "rel:api-1", "min_score": 50.0})
    assert resp.status_code == 201
    gate = resp.json()

    resp = await client.post(f"/api/v1/quality-gates/{gate['id']}/checks", json={"check_type": "test_coverage", "passed": True})
    assert resp.status_code == 201

    resp = await client.post(f"/api/v1/quality-gates/{gate['id']}/evaluate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "passed"


async def test_failure_analysis_flow(client):
    resp = await client.post("/api/v1/failure-patterns", json={"pattern_type": "flaky_test", "subject_ref": "test:api-1"})
    assert resp.status_code == 201

    resp = await client.post("/api/v1/risk-assessments", json={"subject_ref": "rel:api-2", "factors": {"a": 90.0, "b": 95.0}})
    assert resp.status_code == 201
    assert resp.json()["risk_level"] == "critical"

    resp = await client.get("/api/v1/risk-assessments", params={"subject_ref": "rel:api-2"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_certification_flow(client):
    resp = await client.post("/api/v1/certification-runs", json={"release_ref": "rel:api-3"})
    assert resp.status_code == 201
    run = resp.json()

    resp = await client.post(f"/api/v1/certification-runs/{run['id']}/certify", json={"quality_score": 95.0, "security_score": 95.0})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "approved"


async def test_observability_flow(client):
    resp = await client.post("/api/v1/trends", json={"metric_type": "quality", "value": 80.0})
    assert resp.status_code == 201
    resp = await client.post("/api/v1/trends", json={"metric_type": "quality", "value": 95.0})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/trends/quality")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = await client.get("/api/v1/trends/quality/direction")
    assert resp.status_code == 200
    assert resp.json()["direction"] in ("improving", "stable", "declining")


async def test_missing_tenant_header_rejected(app):
    import httpx
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", trust_env=False) as c:
        resp = await c.get("/api/v1/test-suites")
        assert resp.status_code == 400


async def test_not_found_returns_404(client):
    resp = await client.get("/api/v1/test-suites/does-not-exist")
    assert resp.status_code == 404


async def test_unsupported_type_returns_422(client):
    resp = await client.post("/api/v1/test-suites", json={"name": "bad", "test_type": "not-a-type"})
    assert resp.status_code == 422
