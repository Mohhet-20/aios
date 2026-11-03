import pytest


@pytest.mark.asyncio
async def test_metrics_registry_and_compute(client):
    registry_resp = await client.get("/api/v1/metrics/registry")
    assert registry_resp.status_code == 200
    assert len(registry_resp.json()) == 20

    compute_resp = await client.post("/api/v1/metrics/compute", json={
        "metric_keys": ["accuracy", "latency"], "actual_output": "Paris", "expected_output": "Paris", "skip_errors": True,
    })
    assert compute_resp.status_code == 200
    body = compute_resp.json()
    assert body["accuracy"] == 1.0
    assert body["latency"] is None


@pytest.mark.asyncio
async def test_metrics_compute_raises_when_not_skipping_errors(client):
    resp = await client.post("/api/v1/metrics/compute", json={"metric_keys": ["accuracy"], "skip_errors": False})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_metrics_sync_definitions_and_record_result(client):
    sync_resp = await client.post("/api/v1/metrics/sync-definitions")
    assert sync_resp.status_code == 200
    assert len(sync_resp.json()) == 20

    ws = await client.post("/api/v1/workspaces", json={"name": "Metrics Co", "slug": "metrics-co-api", "organization_id": "org-1"})
    workspace_id = ws.json()["id"]

    record_resp = await client.post("/api/v1/metrics/results", json={
        "metric_keys": ["accuracy"], "actual_output": "Paris", "expected_output": "Paris",
        "workspace_id": workspace_id, "subject_type": "adhoc",
    })
    assert record_resp.status_code == 201
    assert record_resp.json()[0]["value"] == 1.0


@pytest.mark.asyncio
async def test_benchmark_run_end_to_end(client):
    ws = await client.post("/api/v1/workspaces", json={"name": "Bench Co", "slug": "bench-co-api", "organization_id": "org-1"})
    workspace_id = ws.json()["id"]

    dataset = (await client.post("/api/v1/datasets", json={
        "workspace_id": workspace_id, "organization_id": "org-1", "name": "Bench Set", "owner_id": "u1", "dataset_type": "golden",
    })).json()
    draft = (await client.post(f"/api/v1/datasets/{dataset['id']}/versions/draft", params={"created_by": "u1"})).json()
    await client.post(f"/api/v1/datasets/versions/{draft['id']}/items", json={
        "items": [{"input_data": {"q": "1+1"}, "expected_output": "2"}],
    })
    await client.post(f"/api/v1/datasets/versions/{draft['id']}/publish")

    benchmark_resp = await client.post("/api/v1/benchmarks", json={
        "workspace_id": workspace_id, "organization_id": "org-1", "name": "Shootout", "owner_id": "u1",
        "benchmark_type": "model", "mode": "ab_test", "dataset_id": dataset["id"], "metric_keys": ["accuracy"],
    })
    assert benchmark_resp.status_code == 201
    benchmark = benchmark_resp.json()

    start_resp = await client.post(f"/api/v1/benchmarks/{benchmark['id']}/runs", json={
        "candidates": [
            {"label": "good", "type": "model", "static_response": "2"},
            {"label": "bad", "type": "model", "static_response": "wrong"},
        ],
        "triggered_by": "u1",
    })
    assert start_resp.status_code == 201
    run = start_resp.json()

    exec_resp = await client.post(f"/api/v1/benchmarks/runs/{run['id']}/execute")
    assert exec_resp.status_code == 200
    assert exec_resp.json()["status"] == "succeeded"

    leaderboard_resp = await client.get(f"/api/v1/benchmarks/runs/{run['id']}/leaderboard")
    assert leaderboard_resp.status_code == 200
    board = leaderboard_resp.json()
    assert board[0]["candidate_label"] == "good"
    assert board[0]["aggregate_score"] == 1.0
