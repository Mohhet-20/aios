import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.config.settings import Settings, get_settings
from agent_platform.core.exceptions import ResourceQuotaExceededError
from agent_platform.models.execution import AgentExecutionModel
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.planner.planning_service import PlanningService
from agent_platform.policies.policy_engine import PolicyEngine


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-policy", organization_id="org1"))


async def _seed_agent(repos, ws_id, *, resource_limits=None, is_autonomous=True):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key("coding")
    agent_svc = AgentService(repos)
    return await agent_svc.create_agent(ws_id, agent_type.id, name="Coder", owner_id="u1", resource_limits=resource_limits, is_autonomous=is_autonomous)


@pytest.mark.asyncio
async def test_check_resource_quota_passes_under_limit(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, resource_limits={"max_concurrent_tasks": 2})

    engine = PolicyEngine(repos, get_settings())
    await engine.check_resource_quota(agent)  # no running executions yet — should not raise


@pytest.mark.asyncio
async def test_check_resource_quota_raises_at_limit(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, resource_limits={"max_concurrent_tasks": 1})
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="running"))

    engine = PolicyEngine(repos, get_settings())
    with pytest.raises(ResourceQuotaExceededError):
        await engine.check_resource_quota(agent)


@pytest.mark.asyncio
async def test_check_resource_quota_no_limit_configured_never_raises(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, resource_limits={})
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="running"))
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="running"))

    engine = PolicyEngine(repos, get_settings())
    await engine.check_resource_quota(agent)  # no configured max_concurrent_tasks -> no gate


@pytest.mark.asyncio
async def test_check_rate_limit_raises_when_exceeded(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    # A fresh Settings instance, not the process-wide get_settings() cache, so this
    # test's override doesn't leak into any other test that reads the cached singleton.
    settings = Settings(rate_limit_tasks_per_minute=2)

    for _ in range(2):
        await repos.executions.add(AgentExecutionModel(agent_id=agent.id, triggered_by="u1", status="completed"))

    engine = PolicyEngine(repos, settings)
    with pytest.raises(ResourceQuotaExceededError):
        await engine.check_rate_limit("u1")


@pytest.mark.asyncio
async def test_requires_approval_for_non_autonomous_agent(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, is_autonomous=False)
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Task", goal="Do a thing", created_by="u1")

    engine = PolicyEngine(repos, get_settings())
    assert engine.requires_approval(agent, task) is True


@pytest.mark.asyncio
async def test_requires_approval_for_sensitive_task_context(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, is_autonomous=True)
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Task", goal="Do a thing", created_by="u1", context={"sensitive": True})

    engine = PolicyEngine(repos, get_settings())
    assert engine.requires_approval(agent, task) is True


@pytest.mark.asyncio
async def test_requires_approval_false_for_normal_autonomous_agent(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, is_autonomous=True)
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Task", goal="Do a thing", created_by="u1")

    engine = PolicyEngine(repos, get_settings())
    assert engine.requires_approval(agent, task) is False
