import httpx
import pytest

from agent_platform.agent_api.application_factory import create_app
from agent_platform.agent_api.dependencies import get_ai_core, get_repos

from tests.conftest import make_response


@pytest.fixture
def anonymous_app(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    application = create_app()
    application.dependency_overrides[get_repos] = lambda: repos
    application.dependency_overrides[get_ai_core] = lambda: context
    return application


@pytest.mark.asyncio
async def test_execute_sequential_requires_actor_header(anonymous_app, repos, scripted_ai_core):
    context, _ = scripted_ai_core
    transport = httpx.ASGITransport(app=anonymous_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:  # no X-User-Id header
        ws = (await client.post("/api/v1/workspaces", json={"name": "WS", "slug": "ws-sec", "organization_id": "org1"})).json()
        root = (await client.post("/api/v1/tasks", json={
            "workspace_id": ws["id"], "title": "Root", "goal": "Root goal", "created_by": "u1",
        })).json()

        resp = await client.post(f"/api/v1/orchestration/{root['id']}/execute-sequential", json={"agent_ids": []})
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_execute_sequential_records_triggered_by_from_actor_header(client, repos, scripted_ai_core):
    _, provider = scripted_ai_core
    ws = (await client.post("/api/v1/workspaces", json={"name": "WS", "slug": "ws-sec2", "organization_id": "org1"})).json()
    await client.post("/api/v1/agent-types/seed-builtin")
    agent_type = (await client.get("/api/v1/agent-types/coding")).json()
    agent = (await client.post("/api/v1/agents", json={
        "workspace_id": ws["id"], "agent_type_id": agent_type["id"], "name": "Coder", "owner_id": "u1",
    })).json()
    agent = (await client.post(f"/api/v1/agents/{agent['id']}/activate")).json()

    root = (await client.post("/api/v1/tasks", json={
        "workspace_id": ws["id"], "title": "Root", "goal": "Root goal", "created_by": "u1",
    })).json()

    provider.push(make_response("done"))
    resp = await client.post(f"/api/v1/orchestration/{root['id']}/execute-sequential", json={"agent_ids": [agent["id"]]})
    assert resp.status_code == 200

    executions = await repos.executions.list_for_task(root["id"])
    assert len(executions) == 1
    assert executions[0].triggered_by == "u1"  # from the client fixture's X-User-Id header
