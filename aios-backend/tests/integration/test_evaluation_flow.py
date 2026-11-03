import pytest


@pytest.mark.asyncio
async def test_evaluation_run_and_complete(client, auth_headers):
    r = await client.post(
        "/api/v1/evaluations",
        json={
            "workspace_id": "ws-eval",
            "suite_name": "Golden Set",
            "target_type": "prompt_version",
            "target_id": "pv-1",
            "dataset_id": "ds-1",
        },
        headers=auth_headers,
    )
    assert r.status_code == 202
    run_id = r.json()["id"]
    assert r.json()["status"] == "queued"

    r = await client.post(
        f"/api/v1/evaluations/{run_id}/complete", params={"passed": 92, "failed": 8}, headers=auth_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["score"] == 92.0
    assert body["total"] == 100
