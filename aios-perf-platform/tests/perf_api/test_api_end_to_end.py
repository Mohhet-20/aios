"""End-to-end HTTP tests driving every module through the real FastAPI
app (in-process ASGI transport, no real network) — the same pattern
used across every other AIOS platform's e2e suite."""
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
async def test_cache_flow(client):
    resp = await client.put("/api/v1/cache/entries", json={"layer": "response", "key": "k1", "value": "hello", "ttl_seconds": 60})
    assert resp.status_code == 200

    resp = await client.get("/api/v1/cache/entries/response/k1")
    assert resp.status_code == 200
    assert resp.json()["value"] == "hello"
    assert resp.json()["found"] is True

    resp = await client.get("/api/v1/cache/stats")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await client.delete("/api/v1/cache/entries/response/k1")
    assert resp.status_code == 200
    assert resp.json()["invalidated"] is True

    resp = await client.post("/api/v1/cache/sweep")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_routing_flow(client):
    resp = await client.put(
        "/api/v1/routing/policies",
        json={"scope_type": "organization", "scope_id": "org-api", "allowed_tiers": ["small", "medium"], "default_tier": "medium"},
    )
    assert resp.status_code == 200

    resp = await client.post(
        "/api/v1/routing/route",
        json={"task_complexity": "expert", "user_tier": "enterprise", "policy_scope_type": "organization", "policy_scope_id": "org-api"},
    )
    assert resp.status_code == 200
    assert resp.json()["chosen_tier"] == "medium"

    resp = await client.get("/api/v1/routing/decisions")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_cost_and_budget_flow(client):
    resp = await client.post(
        "/api/v1/cost/records",
        json={"category": "token", "entity_type": "agent", "entity_id": "agent-api", "amount_usd": 3.0, "unit_count": 1000},
    )
    assert resp.status_code == 201

    resp = await client.get("/api/v1/cost/records/agent/agent-api/total")
    assert resp.status_code == 200
    assert resp.json()["total_usd"] == 3.0

    resp = await client.put("/api/v1/budgets", json={"entity_type": "agent", "entity_id": "agent-api", "limit_usd": 10.0})
    assert resp.status_code == 200

    resp = await client.get("/api/v1/budgets/agent/agent-api/utilization")
    assert resp.status_code == 200
    assert resp.json()["utilization_pct"] == 30.0

    resp = await client.post("/api/v1/budgets/agent/agent-api/check-alerts")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_optimization_flow(client):
    resp = await client.put("/api/v1/cache/entries", json={"layer": "prompt", "key": "cold", "value": "x"})
    assert resp.status_code == 200
    # generate a hit and enough samples for the low-hit-rate rule to fire
    for _ in range(15):
        await client.get("/api/v1/cache/entries/prompt/missing-key")
    await client.get("/api/v1/cache/entries/prompt/cold")

    resp = await client.post("/api/v1/recommendations/generate/cache")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/recommendations")
    assert resp.status_code == 200
    recs = resp.json()
    if recs:
        rec_id = recs[0]["id"]
        resp = await client.post(f"/api/v1/recommendations/{rec_id}/accept")
        assert resp.status_code == 200
        resp = await client.post(f"/api/v1/recommendations/{rec_id}/apply")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_observability_and_benchmark_flow(client):
    resp = await client.post("/api/v1/observability/latency", json={"operation": "api-op", "duration_ms": 120.0})
    assert resp.status_code == 200

    resp = await client.get("/api/v1/observability/latency/api-op/percentiles")
    assert resp.status_code == 200
    assert resp.json()["sample_count"] == 1

    resp = await client.get("/api/v1/observability/latency/api-op/slo")
    assert resp.status_code == 200

    resp = await client.post("/api/v1/observability/throughput", json={"operation": "api-op", "request_count": 100, "window_seconds": 10})
    assert resp.status_code == 200

    resp = await client.get("/api/v1/observability/throughput/api-op/rate")
    assert resp.status_code == 200
    assert resp.json()["requests_per_second"] == 10.0

    resp = await client.post("/api/v1/benchmarks", json={"name": "api-benchmark"})
    assert resp.status_code == 201
    run_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/benchmarks/{run_id}/complete", json={"baseline_ms": 200.0, "optimized_ms": 20.0})
    assert resp.status_code == 200
    assert resp.json()["improvement_pct"] == 90.0

    resp = await client.get("/api/v1/benchmarks")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_gpu_pool_flow(client):
    resp = await client.post("/api/v1/gpu-pools", json={"name": "api-pool", "pool_type": "shared", "gpu_count": 4})
    assert resp.status_code == 201
    pool_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/gpu-pools/{pool_id}/utilization", json={"utilization_pct": 10.0})
    assert resp.status_code == 200

    resp = await client.get("/api/v1/gpu-pools/underutilized")
    assert resp.status_code == 200
    assert any(p["id"] == pool_id for p in resp.json())

    resp = await client.post(f"/api/v1/gpu-pools/{pool_id}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_missing_tenant_header_rejected(client):
    client.headers.pop("X-Tenant-Id")
    resp = await client.get("/api/v1/cache/stats")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_unsupported_cache_layer_returns_422(client):
    resp = await client.get("/api/v1/cache/entries/not-a-layer/k")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_budget_not_found_returns_404(client):
    resp = await client.get("/api/v1/budgets/user/no-such-user")
    assert resp.status_code == 404
