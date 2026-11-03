import pytest


async def _make_workspace(client):
    resp = await client.post("/api/v1/workspaces", json={"name": "DS Co", "slug": "ds-co", "organization_id": "org-1"})
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_dataset_lifecycle_and_sharing(client):
    workspace_id = await _make_workspace(client)
    other_ws = await client.post("/api/v1/workspaces", json={"name": "DS Co 2", "slug": "ds-co-2", "organization_id": "org-1"})
    other_workspace_id = other_ws.json()["id"]

    create_resp = await client.post("/api/v1/datasets", json={
        "workspace_id": workspace_id, "organization_id": "org-1", "name": "API Set", "owner_id": "u1", "dataset_type": "golden",
    })
    assert create_resp.status_code == 201
    dataset = create_resp.json()

    draft_resp = await client.post(f"/api/v1/datasets/{dataset['id']}/versions/draft", params={"created_by": "u1"})
    assert draft_resp.status_code == 200
    version = draft_resp.json()

    items_resp = await client.post(f"/api/v1/datasets/versions/{version['id']}/items", json={
        "items": [{"input_data": {"q": "1+1"}, "expected_output": "2"}],
    })
    assert items_resp.status_code == 200
    assert items_resp.json()["item_count"] == 1

    list_items_resp = await client.get(f"/api/v1/datasets/versions/{version['id']}/items")
    assert list_items_resp.status_code == 200
    assert len(list_items_resp.json()) == 1

    publish_resp = await client.post(f"/api/v1/datasets/versions/{version['id']}/publish")
    assert publish_resp.status_code == 200
    assert publish_resp.json()["status"] == "published"

    share_resp = await client.post(f"/api/v1/datasets/{dataset['id']}/share", params={"target_workspace_id": other_workspace_id})
    assert share_resp.status_code == 200

    shared_resp = await client.get(f"/api/v1/datasets/shared/{other_workspace_id}", params={"organization_id": "org-1"})
    assert shared_resp.status_code == 200
    assert len(shared_resp.json()) == 1

    list_resp = await client.get("/api/v1/datasets", params={"workspace_id": workspace_id})
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_evaluation_run_end_to_end(client):
    workspace_id = await _make_workspace(client)

    dataset = (await client.post("/api/v1/datasets", json={
        "workspace_id": workspace_id, "organization_id": "org-1", "name": "Run Set", "owner_id": "u1", "dataset_type": "golden",
    })).json()
    draft = (await client.post(f"/api/v1/datasets/{dataset['id']}/versions/draft", params={"created_by": "u1"})).json()
    await client.post(f"/api/v1/datasets/versions/{draft['id']}/items", json={
        "items": [{"input_data": {"q": "1+1"}, "expected_output": "2"}],
    })
    await client.post(f"/api/v1/datasets/versions/{draft['id']}/publish")

    evaluation = (await client.post("/api/v1/evaluations", json={
        "workspace_id": workspace_id, "organization_id": "org-1", "name": "Run Eval", "owner_id": "u1", "category": "prompt",
    })).json()
    eval_draft = (await client.post(f"/api/v1/evaluations/{evaluation['id']}/versions/draft", params={"created_by": "u1"})).json()
    await client.patch(f"/api/v1/evaluations/versions/{eval_draft['id']}", json={
        "dataset_id": dataset["id"], "metric_keys": ["accuracy"], "pass_threshold": 1.0,
        "target_config": {"type": "prompt", "static_response": "2"},
    })
    await client.post(f"/api/v1/evaluations/versions/{eval_draft['id']}/publish")

    start_resp = await client.post("/api/v1/runs", json={"evaluation_id": evaluation["id"], "triggered_by": "u1"})
    assert start_resp.status_code == 201
    run = start_resp.json()
    assert run["status"] == "pending"

    exec_resp = await client.post(f"/api/v1/runs/{run['id']}/execute")
    assert exec_resp.status_code == 200
    completed = exec_resp.json()
    assert completed["status"] == "succeeded"
    assert completed["overall_score"] == 1.0

    list_resp = await client.get("/api/v1/runs", params={"evaluation_id": evaluation["id"]})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    results_resp = await client.get(f"/api/v1/runs/{run['id']}/item-results")
    assert results_resp.status_code == 200
    assert results_resp.json()[0]["passed"] is True
