import json

import pytest

from tests.conftest import make_response


async def _seed_workspace_and_agent(client, *, type_key="coding", name="Agent", memory_access=None):
    ws = (await client.post("/api/v1/workspaces", json={"name": "WS", "slug": f"ws-{type_key}-{name}".lower(), "organization_id": "org1"})).json()
    await client.post("/api/v1/agent-types/seed-builtin")
    agent_type = (await client.get(f"/api/v1/agent-types/{type_key}")).json()
    agent = (await client.post("/api/v1/agents", json={
        "workspace_id": ws["id"], "agent_type_id": agent_type["id"], "name": name, "owner_id": "u1",
        "memory_access": memory_access or {},
    })).json()
    agent = (await client.post(f"/api/v1/agents/{agent['id']}/activate")).json()
    return ws, agent


def _decomposition_response(subtasks):
    return json.dumps({"rationale": "test", "subtasks": subtasks})


@pytest.mark.asyncio
async def test_planning_flow(client, scripted_ai_core):
    _, provider = scripted_ai_core
    ws, agent = await _seed_workspace_and_agent(client)

    root_resp = await client.post("/api/v1/tasks", json={
        "workspace_id": ws["id"], "title": "Ship it", "goal": "Ship the feature", "created_by": "u1",
    })
    assert root_resp.status_code == 201
    root = root_resp.json()
    assert root["root_task_id"] == root["id"]

    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "do A", "priority": "high", "depends_on": [], "estimated_tokens": 10, "estimated_duration_seconds": 5},
        {"title": "B", "goal": "do B", "priority": "normal", "depends_on": [0], "estimated_tokens": 20, "estimated_duration_seconds": 10},
    ])))
    decompose_resp = await client.post(f"/api/v1/tasks/{root['id']}/decompose", json={"max_subtasks": 8})
    assert decompose_resp.status_code == 201
    subtasks = decompose_resp.json()
    assert len(subtasks) == 2

    order_resp = await client.get(f"/api/v1/tasks/{root['id']}/execution-order")
    # execution-order walks the whole root_task_id subtree, which includes the
    # root task itself alongside its two decomposed subtasks.
    assert len(order_resp.json()["order"]) == 3

    progress_resp = await client.get(f"/api/v1/tasks/{root['id']}/progress")
    assert progress_resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_orchestration_execute_sequential_and_delegate(client, scripted_ai_core):
    _, provider = scripted_ai_core
    ws, agent = await _seed_workspace_and_agent(client)
    _, agent2 = await _seed_workspace_and_agent(client, name="Second")

    root = (await client.post("/api/v1/tasks", json={
        "workspace_id": ws["id"], "title": "Root", "goal": "Root goal", "created_by": "u1",
    })).json()

    delegate_resp = await client.post(f"/api/v1/orchestration/{root['id']}/delegate", json={
        "to_agent_id": agent["id"], "reason": "best fit",
    })
    assert delegate_resp.status_code == 201
    assert delegate_resp.json()["status"] == "accepted"

    provider.push(make_response("root task done"))
    exec_resp = await client.post(f"/api/v1/orchestration/{root['id']}/execute-sequential", json={
        "agent_ids": [agent["id"], agent2["id"]],
    })
    assert exec_resp.status_code == 200
    results = exec_resp.json()
    assert results[root["id"]]["status"] == "completed"


@pytest.mark.asyncio
async def test_communication_direct_message_and_conversation(client):
    ws, agent_a = await _seed_workspace_and_agent(client, name="A")
    _, agent_b = await _seed_workspace_and_agent(client, name="B")
    root = (await client.post("/api/v1/tasks", json={
        "workspace_id": ws["id"], "title": "Root", "goal": "Root goal", "created_by": "u1",
    })).json()

    send_resp = await client.post("/api/v1/communication/messages/direct", json={
        "task_id": root["id"], "from_agent_id": agent_a["id"], "to_agent_id": agent_b["id"], "content": "hello",
    })
    assert send_resp.status_code == 201

    convo_resp = await client.get(f"/api/v1/communication/tasks/{root['id']}/conversation")
    assert len(convo_resp.json()) == 1
    assert convo_resp.json()[0]["content"] == "hello"


@pytest.mark.asyncio
async def test_reasoning_think_and_reflection_critique(client, scripted_ai_core):
    _, provider = scripted_ai_core
    ws, agent = await _seed_workspace_and_agent(client, type_key="reasoning")
    root = (await client.post("/api/v1/tasks", json={
        "workspace_id": ws["id"], "title": "Solve", "goal": "Solve the puzzle", "created_by": "u1",
    })).json()

    provider.push(make_response(json.dumps({
        "steps": [{"step": 1, "thought": "thinking", "action": None, "observation": None}],
        "final_answer": "42", "confidence": 0.9,
    })))
    think_resp = await client.post("/api/v1/reasoning/think", json={"agent_id": agent["id"], "task_id": root["id"]})
    assert think_resp.status_code == 201
    assert think_resp.json()["final_answer"] == "42"

    traces_resp = await client.get(f"/api/v1/tasks/{root['id']}/reasoning-traces")
    assert len(traces_resp.json()) == 1

    provider.push(make_response(json.dumps({
        "critique": "looks good", "passed": True, "issues": [], "suggested_correction": None, "confidence": 0.8,
    })))
    critique_resp = await client.post("/api/v1/reflection/critique", json={
        "response_content": "here's my work", "task_id": root["id"], "reflecting_agent_id": agent["id"], "execution_id": "exec-1",
    })
    assert critique_resp.status_code == 201
    assert critique_resp.json()["passed_verification"] is True


@pytest.mark.asyncio
async def test_tools_available_and_invoke(client, scripted_ai_core):
    context, _ = scripted_ai_core
    ws, agent = await _seed_workspace_and_agent(client)

    from ai_core.schemas.tools import ToolDefinition

    async def _adder(**kwargs):
        return kwargs["a"] + kwargs["b"]

    context.tool_registry.register(
        ToolDefinition(name="calculator", description="adds", parameters={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}),
        _adder,
    )
    await client.post(f"/api/v1/agents/{agent['id']}/tool-permissions", json={"tool_name": "calculator", "level": "execute", "granted_by": "u1"})

    available_resp = await client.get(f"/api/v1/agents/{agent['id']}/tools")
    assert any(t["name"] == "calculator" for t in available_resp.json())

    invoke_resp = await client.post(f"/api/v1/agents/{agent['id']}/tools/invoke", json={
        "tool_call_id": "tc1", "name": "calculator", "arguments": {"a": 2, "b": 3},
    })
    assert invoke_resp.status_code == 200
    assert invoke_resp.json()["content"] == 5


@pytest.mark.asyncio
async def test_memory_remember_recall_and_forget(client):
    ws, agent = await _seed_workspace_and_agent(client, memory_access={"short_term": True})

    put_resp = await client.put(f"/api/v1/agents/{agent['id']}/memory", json={"key": "color", "value": "blue"})
    assert put_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/agents/{agent['id']}/memory/color")
    assert get_resp.json()["value"] == "blue"

    del_resp = await client.delete(f"/api/v1/agents/{agent['id']}/memory/color")
    assert del_resp.status_code == 204

    get_after_resp = await client.get(f"/api/v1/agents/{agent['id']}/memory/color")
    assert get_after_resp.json()["value"] is None


@pytest.mark.asyncio
async def test_governance_rbac_and_approval_flow(client):
    ws, agent = await _seed_workspace_and_agent(client)
    root = (await client.post("/api/v1/tasks", json={
        "workspace_id": ws["id"], "title": "Sensitive", "goal": "Do something sensitive", "created_by": "u1",
    })).json()

    grant_resp = await client.post("/api/v1/rbac/grants", json={
        "principal_id": "u2", "resource_type": "workspace", "resource_id": ws["id"], "role": "operator", "granted_by": "u1",
    })
    assert grant_resp.status_code == 201
    grants_resp = await client.get("/api/v1/rbac/principals/u2/grants")
    assert len(grants_resp.json()) == 1

    gate_resp = await client.post(f"/api/v1/tasks/{root['id']}/approval-gates", json={"reason": "needs review", "requested_by_agent_id": agent["id"]})
    assert gate_resp.status_code == 201
    gate = gate_resp.json()

    pending_resp = await client.get("/api/v1/approval-gates/pending")
    assert any(g["id"] == gate["id"] for g in pending_resp.json())

    approve_resp = await client.post(f"/api/v1/approval-gates/{gate['id']}/approve", json={"approver_id": "human-1"})
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    audit_resp = await client.post("/api/v1/audit-log", json={
        "actor_id": "human-1", "action": "approval.approve", "resource_type": "task", "resource_id": root["id"],
    })
    assert audit_resp.status_code == 201
    list_audit_resp = await client.get(f"/api/v1/audit-log/task/{root['id']}")
    assert len(list_audit_resp.json()) == 1


@pytest.mark.asyncio
async def test_observability_and_evaluation_endpoints(client, scripted_ai_core):
    _, provider = scripted_ai_core
    ws, agent = await _seed_workspace_and_agent(client)
    root = (await client.post("/api/v1/tasks", json={
        "workspace_id": ws["id"], "title": "Root", "goal": "Root goal", "created_by": "u1",
    })).json()

    provider.push(make_response("done"))
    await client.post(f"/api/v1/orchestration/{root['id']}/execute-sequential", json={"agent_ids": [agent["id"]]})

    timeline_resp = await client.get(f"/api/v1/tasks/{root['id']}/execution-timeline")
    assert timeline_resp.status_code == 200
    assert len(timeline_resp.json()) >= 1

    health_resp = await client.get(f"/api/v1/agents/{agent['id']}/health-summary")
    assert health_resp.status_code == 200
    assert health_resp.json()["execution_count"] >= 1

    rollup_resp = await client.get("/api/v1/analytics/cost-rollup", params={"agent_id": agent["id"]})
    assert rollup_resp.status_code == 200

    success_rate_resp = await client.get(f"/api/v1/tasks/{root['id']}/evaluation/task-success-rate")
    assert success_rate_resp.status_code == 200
