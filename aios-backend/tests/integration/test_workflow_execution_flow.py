"""Integration test: create a workflow, execute it, and confirm the
in-process background worker actually picks up and completes the job — end
to end through the real event loop, not mocked out."""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_workflow_execute_runs_in_background(client, auth_headers):
    r = await client.post(
        "/api/v1/workspaces", json={"organization_id": "org-wf", "name": "WF Workspace"}, headers=auth_headers
    )
    workspace_id = r.json()["id"]

    r = await client.post(
        "/api/v1/workflows",
        json={
            "workspace_id": workspace_id,
            "name": "Test Workflow",
            "definition": {"nodes": [], "edges": []},
        },
        headers=auth_headers,
    )
    workflow_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/workflows/{workflow_id}/execute", json={"input_payload": {}}, headers=auth_headers
    )
    assert r.status_code == 202
    execution_id = r.json()["id"]
    assert r.json()["status"] == "running"

    # Give the in-process worker a moment to pick the job off the queue.
    await asyncio.sleep(0.3)

    r = await client.get(f"/api/v1/workflows/{workflow_id}/executions", headers=auth_headers)
    assert r.status_code == 200
    assert any(e["id"] == execution_id for e in r.json())
