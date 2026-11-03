import pytest

from tool_platform.core.exceptions import ApprovalRequiredError, ConcurrencyLimitExceededError
from tests.governance.conftest import make_published_tool


@pytest.mark.asyncio
async def test_sensitive_tool_blocked_without_approval_gate(engine, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, sensitivity_level="high")
    with pytest.raises(ApprovalRequiredError):
        await engine.start_execution(tool.id, triggered_by="user-1")


@pytest.mark.asyncio
async def test_sensitive_tool_runs_with_a_valid_consumed_approval_gate(
    engine, approval_service, tool_service, version_service, workspace
):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, sensitivity_level="critical")

    gate = await approval_service.request_approval("tool", tool.id, requested_by="user-1", reason="needed for demo")
    await approval_service.approve(gate.id, approver_id="admin-1")

    execution = await engine.start_execution(tool.id, triggered_by="user-1", approval_gate_id=gate.id)
    assert execution.status == "succeeded"


@pytest.mark.asyncio
async def test_same_approval_gate_cannot_be_reused_for_a_second_execution(
    engine, approval_service, tool_service, version_service, workspace
):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, sensitivity_level="high")
    gate = await approval_service.request_approval("tool", tool.id, requested_by="user-1")
    await approval_service.approve(gate.id, approver_id="admin-1")

    await engine.start_execution(tool.id, triggered_by="user-1", approval_gate_id=gate.id)

    with pytest.raises(Exception):
        await engine.start_execution(tool.id, triggered_by="user-1", approval_gate_id=gate.id)


@pytest.mark.asyncio
async def test_normal_sensitivity_tool_does_not_require_approval(engine, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, sensitivity_level="normal")
    execution = await engine.start_execution(tool.id, triggered_by="user-1")
    assert execution.status == "succeeded"


@pytest.mark.asyncio
async def test_workspace_concurrency_quota_blocks_new_executions(repos, tool_service, version_service, workspace):
    from tool_platform.config.settings import Settings
    from tool_platform.governance.policy_engine import PolicyEngine
    from tool_platform.tool_execution.engine import ToolExecutionEngine
    from tool_platform.tool_execution.registry import build_default_connector_registry

    tight_engine = ToolExecutionEngine(
        repos, build_default_connector_registry(),
        policy_engine=PolicyEngine(repos, Settings(workspace_max_concurrent_executions=0)),
    )
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    with pytest.raises(ConcurrencyLimitExceededError):
        await tight_engine.start_execution(tool.id, triggered_by="user-1")


@pytest.mark.asyncio
async def test_audit_log_records_tool_execute_action(engine, audit_service, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    await engine.start_execution(tool.id, triggered_by="user-1")

    entries = await audit_service.list_for_resource("tool", tool.id)
    assert any(e.action == "tool.execute" for e in entries)
