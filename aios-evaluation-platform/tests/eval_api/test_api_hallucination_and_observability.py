import pytest


@pytest.mark.asyncio
async def test_hallucination_check_run_and_list(client):
    ws = await client.post("/api/v1/workspaces", json={"name": "Halluc Co", "slug": "halluc-co-api", "organization_id": "org-1"})
    workspace_id = ws.json()["id"]

    run_resp = await client.post("/api/v1/hallucination-checks", json={
        "workspace_id": workspace_id, "claim_text": "Paris is the capital of France.",
        "source_context": ["Paris is the capital of France."], "subject_type": "adhoc",
    })
    assert run_resp.status_code == 201
    result = run_resp.json()
    assert result["grounded"] is True

    check_resp = await client.post("/api/v1/hallucination-checks", json={
        "workspace_id": workspace_id, "claim_text": "grounded claim two", "source_context": ["grounded claim two context"],
        "subject_type": "evaluation_item", "subject_id": "item-1",
    })
    assert check_resp.status_code == 201

    list_resp = await client.get("/api/v1/hallucination-checks", params={"subject_type": "evaluation_item", "subject_id": "item-1"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_hallucination_check_rejects_missing_context(client):
    ws = await client.post("/api/v1/workspaces", json={"name": "Halluc Co 2", "slug": "halluc-co-api-2", "organization_id": "org-1"})
    workspace_id = ws.json()["id"]
    resp = await client.post("/api/v1/hallucination-checks", json={
        "workspace_id": workspace_id, "claim_text": "x", "source_context": [], "subject_type": "adhoc",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_observability_ingest_and_query(client):
    ws = await client.post("/api/v1/workspaces", json={"name": "Obs Co", "slug": "obs-co-api", "organization_id": "org-1"})
    workspace_id = ws.json()["id"]

    ingest_resp = await client.post("/api/v1/observability/events", json={
        "workspace_id": workspace_id, "event_type": "tool_call", "source_platform": "tool_platform", "status": "succeeded",
        "source_execution_id": "exec-1", "latency_ms": 120.0, "cost": 0.01,
    })
    assert ingest_resp.status_code == 201

    await client.post("/api/v1/observability/events", json={
        "workspace_id": workspace_id, "event_type": "tool_call", "source_platform": "tool_platform", "status": "failed",
        "error_type": "TimeoutError",
    })

    timeline_resp = await client.get("/api/v1/observability/timeline", params={"workspace_id": workspace_id, "source_execution_id": "exec-1"})
    assert timeline_resp.status_code == 200
    assert len(timeline_resp.json()) == 1

    latency_resp = await client.get("/api/v1/observability/stats/latency", params={"workspace_id": workspace_id})
    assert latency_resp.status_code == 200
    assert latency_resp.json()["sample_count"] == 1

    failure_resp = await client.get("/api/v1/observability/stats/failures", params={"workspace_id": workspace_id})
    assert failure_resp.status_code == 200
    assert failure_resp.json()["failure_count"] == 1

    cost_resp = await client.get("/api/v1/observability/stats/tokens-and-cost", params={"workspace_id": workspace_id})
    assert cost_resp.status_code == 200
    assert cost_resp.json()["total_cost"] == 0.01
