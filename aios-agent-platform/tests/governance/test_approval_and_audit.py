import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.domain.enums import ApprovalStatus, TaskStatus
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.planner.planning_service import PlanningService
from agent_platform.policies.approval_service import ApprovalService
from agent_platform.policies.audit_service import AuditService


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-gov", organization_id="org1"))


async def _seed_agent(repos, ws_id):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key("coding")
    agent_svc = AgentService(repos)
    return await agent_svc.create_agent(ws_id, agent_type.id, name="Coder", owner_id="u1")


@pytest.mark.asyncio
async def test_request_approval_moves_task_to_waiting_approval(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Sensitive op", goal="Do something sensitive", created_by="u1")

    svc = ApprovalService(repos)
    gate = await svc.request_approval(task, reason="non-autonomous agent", requested_by_agent_id=agent.id)

    assert gate.status == ApprovalStatus.PENDING.value
    refreshed = await repos.tasks.get_or_404(task.id)
    assert refreshed.status == TaskStatus.WAITING_APPROVAL.value

    pending = await svc.list_pending()
    assert any(g.id == gate.id for g in pending)


@pytest.mark.asyncio
async def test_approve_resumes_task_to_in_progress(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Sensitive op", goal="Do something sensitive", created_by="u1")

    svc = ApprovalService(repos)
    gate = await svc.request_approval(task, reason="needs review", requested_by_agent_id=agent.id)
    approved = await svc.approve(gate.id, approver_id="human-1", notes="looks fine")

    assert approved.status == ApprovalStatus.APPROVED.value
    assert approved.approver_id == "human-1"
    refreshed = await repos.tasks.get_or_404(task.id)
    assert refreshed.status == TaskStatus.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_reject_fails_task(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Sensitive op", goal="Do something sensitive", created_by="u1")

    svc = ApprovalService(repos)
    gate = await svc.request_approval(task, reason="needs review", requested_by_agent_id=agent.id)
    rejected = await svc.reject(gate.id, approver_id="human-1", notes="too risky")

    assert rejected.status == ApprovalStatus.REJECTED.value
    refreshed = await repos.tasks.get_or_404(task.id)
    assert refreshed.status == TaskStatus.FAILED.value
    assert "too risky" in refreshed.failure_reason


@pytest.mark.asyncio
async def test_audit_service_records_and_lists(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    svc = AuditService(repos)
    await svc.record("u1", "agent.activate", "agent", agent.id, before={"status": "draft"}, after={"status": "active"})
    await svc.record("u1", "agent.pause", "agent", agent.id, before={"status": "active"}, after={"status": "paused"})

    entries = await svc.list_for_resource("agent", agent.id)
    assert len(entries) == 2
    assert entries[0].action == "agent.pause"  # most recent first
