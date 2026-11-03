import pytest

from tool_platform.core.exceptions import ConcurrencyLimitExceededError, RateLimitExceededError
from tool_platform.config.settings import Settings
from tool_platform.governance.policy_engine import PolicyEngine
from tests.governance.conftest import make_published_tool


@pytest.mark.asyncio
async def test_requires_approval_true_for_high_and_critical(policy_engine, tool_service, version_service, workspace):
    _tool, high_version = await make_published_tool(tool_service, version_service, workspace, sensitivity_level="high")
    _tool2, critical_version = await make_published_tool(tool_service, version_service, workspace, name="T2", sensitivity_level="critical")
    _tool3, normal_version = await make_published_tool(tool_service, version_service, workspace, name="T3", sensitivity_level="normal")

    assert policy_engine.requires_approval(high_version) is True
    assert policy_engine.requires_approval(critical_version) is True
    assert policy_engine.requires_approval(normal_version) is False


@pytest.mark.asyncio
async def test_rate_limit_trips_after_threshold(repos, tool_service, version_service, workspace):
    engine_policy = PolicyEngine(repos, Settings(rate_limit_calls_per_minute=2))
    tool, _version = await make_published_tool(tool_service, version_service, workspace)

    from tool_platform.tool_execution.engine import ToolExecutionEngine
    from tool_platform.tool_execution.registry import build_default_connector_registry

    engine = ToolExecutionEngine(repos, build_default_connector_registry())
    await engine.start_execution(tool.id, triggered_by="busy-user")

    # only 1 call so far, still under the limit of 2
    await engine_policy.check_rate_limit("busy-user")

    await engine.start_execution(tool.id, triggered_by="busy-user")

    # 2 calls issued, at the limit — the next attempt must be blocked
    with pytest.raises(RateLimitExceededError):
        await engine_policy.check_rate_limit("busy-user")


@pytest.mark.asyncio
async def test_tool_concurrency_quota_enforced(repos, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    engine_policy = PolicyEngine(repos, Settings(max_concurrent_tool_executions=0))

    with pytest.raises(ConcurrencyLimitExceededError):
        await engine_policy.check_tool_concurrency_quota(tool)


@pytest.mark.asyncio
async def test_workspace_concurrency_quota_enforced(repos, workspace):
    engine_policy = PolicyEngine(repos, Settings(workspace_max_concurrent_executions=0))
    with pytest.raises(ConcurrencyLimitExceededError):
        await engine_policy.check_workspace_concurrency_quota(workspace.id)
