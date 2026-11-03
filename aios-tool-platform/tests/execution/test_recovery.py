from datetime import timedelta

import pytest

from tests.execution.conftest import make_engine, make_published_tool
from tool_platform.database.base import utcnow
from tool_platform.domain.enums import ExecutionStatus
from tool_platform.models.execution import ToolExecutionModel


@pytest.mark.asyncio
async def test_sweep_cancels_genuinely_stalled_running_execution(repos, workspace, tool_service, version_service):
    tool, version = await make_published_tool(tool_service, version_service, workspace)
    stale = await repos.executions.add(ToolExecutionModel(
        tool_id=tool.id, tool_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, started_at=utcnow() - timedelta(hours=2), triggered_by="u1",
    ))

    engine = make_engine(repos)
    recovered = await engine.sweep_stalled_executions(stalled_after_seconds=3600)

    assert len(recovered) == 1
    assert recovered[0].id == stale.id
    assert recovered[0].status == ExecutionStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_sweep_leaves_fresh_running_executions_alone(repos, workspace, tool_service, version_service):
    tool, version = await make_published_tool(tool_service, version_service, workspace)
    fresh = await repos.executions.add(ToolExecutionModel(
        tool_id=tool.id, tool_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, started_at=utcnow(), triggered_by="u1",
    ))

    engine = make_engine(repos)
    recovered = await engine.sweep_stalled_executions(stalled_after_seconds=3600)

    assert recovered == []
    refreshed = await repos.executions.get_or_404(fresh.id)
    assert refreshed.status == ExecutionStatus.RUNNING.value


@pytest.mark.asyncio
async def test_sweep_logs_recovery_reason(repos, workspace, tool_service, version_service):
    tool, version = await make_published_tool(tool_service, version_service, workspace)
    stale = await repos.executions.add(ToolExecutionModel(
        tool_id=tool.id, tool_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, started_at=utcnow() - timedelta(hours=2), triggered_by="u1",
    ))

    engine = make_engine(repos)
    await engine.sweep_stalled_executions(stalled_after_seconds=3600)

    logs = await repos.execution_logs.list_for_execution(stale.id)
    assert any("recovered" in log.message for log in logs)
