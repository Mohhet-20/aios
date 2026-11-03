import asyncio
import time

import pytest

from tests.execution.conftest import make_engine, make_published_tool
from tool_platform.core.exceptions import ToolExecutionError, ValidationError
from tool_platform.domain.enums import ExecutionStatus
from tool_platform.tool_execution.handlers.base import ConnectorHandler
from tool_platform.tool_execution.registry import ConnectorRegistry


@pytest.mark.asyncio
async def test_simple_echo_execution_succeeds(repos, workspace, tool_service, version_service):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    engine = make_engine(repos)
    execution = await engine.start_execution(tool.id, input_data={"foo": "bar"})
    assert execution.status == ExecutionStatus.SUCCEEDED.value
    assert execution.output_data == {"foo": "bar"}
    assert execution.completed_at is not None


@pytest.mark.asyncio
async def test_input_schema_validation_failure(repos, workspace, tool_service, version_service):
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace,
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    )
    engine = make_engine(repos)
    execution = await engine.start_execution(tool.id, input_data={"wrong_field": "x"})
    assert execution.status == ExecutionStatus.FAILED.value
    assert "input failed schema validation" in execution.error_message


@pytest.mark.asyncio
async def test_output_schema_validation_failure(repos, workspace, tool_service, version_service):
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace,
        output_schema={"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"]},
    )
    engine = make_engine(repos)
    # EchoHandler reflects input_data as output — giving it no "count" key fails output validation.
    execution = await engine.start_execution(tool.id, input_data={"no_count_here": True})
    assert execution.status == ExecutionStatus.FAILED.value
    assert "output failed schema validation" in execution.error_message


class AlwaysFailsHandler(ConnectorHandler):
    async def execute(self, ctx):
        raise ToolExecutionError("simulated connector failure")


class FlakyHandler(ConnectorHandler):
    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    async def execute(self, ctx):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ToolExecutionError(f"transient failure #{self.calls}")
        return {"ok": True}


class SlowHandler(ConnectorHandler):
    def __init__(self, delay: float):
        self.delay = delay

    async def execute(self, ctx):
        await asyncio.sleep(self.delay)
        return {"done": True}


@pytest.mark.asyncio
async def test_retry_then_succeed(repos, workspace, tool_service, version_service):
    handler = FlakyHandler(fail_times=2)
    connectors = ConnectorRegistry({"flaky": handler})
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace, connector_key="flaky", default_max_retries=3,
    )
    engine = make_engine(repos, connectors)
    execution = await engine.start_execution(tool.id, input_data={})
    assert execution.status == ExecutionStatus.SUCCEEDED.value
    assert execution.output_data == {"ok": True}
    assert execution.attempt_number == 3  # failed twice, succeeded on the 3rd


@pytest.mark.asyncio
async def test_retry_exhausted_fails_permanently(repos, workspace, tool_service, version_service):
    connectors = ConnectorRegistry({"always_fails": AlwaysFailsHandler()})
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace, connector_key="always_fails", default_max_retries=2,
    )
    engine = make_engine(repos, connectors)
    execution = await engine.start_execution(tool.id, input_data={})
    assert execution.status == ExecutionStatus.FAILED.value
    assert execution.attempt_number == 3  # 1 initial + 2 retries, all failed
    assert "permanently" in execution.error_message or "simulated" in execution.error_message


@pytest.mark.asyncio
async def test_timeout_is_enforced(repos, workspace, tool_service, version_service):
    connectors = ConnectorRegistry({"slow": SlowHandler(delay=1.5)})
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace, connector_key="slow", default_timeout_seconds=1, default_max_retries=0,
    )
    engine = make_engine(repos, connectors)
    execution = await engine.start_execution(tool.id, input_data={})
    assert execution.status == ExecutionStatus.TIMED_OUT.value


@pytest.mark.asyncio
async def test_manual_retry_after_exhaustion(repos, workspace, tool_service, version_service):
    handler = FlakyHandler(fail_times=1)
    connectors = ConnectorRegistry({"flaky": handler})
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace, connector_key="flaky", default_max_retries=0,
    )
    engine = make_engine(repos, connectors)
    execution = await engine.start_execution(tool.id, input_data={})
    assert execution.status == ExecutionStatus.FAILED.value

    retried = await engine.retry_execution(execution.id)
    assert retried.status == ExecutionStatus.SUCCEEDED.value


@pytest.mark.asyncio
async def test_cancel_pending_execution(repos, workspace, tool_service, version_service):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    engine = make_engine(repos)
    from tool_platform.models.execution import ToolExecutionModel
    execution = await repos.executions.add(ToolExecutionModel(
        tool_id=tool.id, tool_version_id=tool.current_version_id, workspace_id=workspace.id,
    ))
    cancelled = await engine.cancel_execution(execution.id)
    assert cancelled.status == ExecutionStatus.CANCELLED.value


class CompensableHandler(ConnectorHandler):
    def __init__(self):
        self.compensated = False

    async def execute(self, ctx):
        raise ToolExecutionError("fails so we can test rollback")

    async def compensate(self, ctx):
        self.compensated = True


@pytest.mark.asyncio
async def test_rollback_calls_compensate(repos, workspace, tool_service, version_service):
    handler = CompensableHandler()
    connectors = ConnectorRegistry({"compensable": handler})
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace, connector_key="compensable", default_max_retries=0,
    )
    engine = make_engine(repos, connectors)
    execution = await engine.start_execution(tool.id, input_data={})
    assert execution.status == ExecutionStatus.FAILED.value

    rolled_back = await engine.rollback_execution(execution.id)
    assert rolled_back.status == ExecutionStatus.ROLLED_BACK.value
    assert handler.compensated is True


@pytest.mark.asyncio
async def test_checkpoints_are_written(repos, workspace, tool_service, version_service):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    engine = make_engine(repos)
    execution = await engine.start_execution(tool.id, input_data={})
    checkpoints = await repos.checkpoints.list_for_execution(execution.id)
    assert len(checkpoints) >= 1


@pytest.mark.asyncio
async def test_run_batch_parallel_is_genuinely_concurrent(repos, workspace, tool_service, version_service):
    branch_count = 6
    branch_delay = 0.05
    connectors = ConnectorRegistry({"slow": SlowHandler(delay=branch_delay)})
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="slow")
    engine = make_engine(repos, connectors)

    started = time.monotonic()
    parent, children = await engine.run_batch(tool.id, [{"i": i} for i in range(branch_count)], execution_mode="parallel")
    elapsed = time.monotonic() - started

    assert parent.status == ExecutionStatus.SUCCEEDED.value
    assert len(children) == branch_count
    assert all(c.status == ExecutionStatus.SUCCEEDED.value for c in children)
    assert elapsed < branch_count * branch_delay * 0.75  # true concurrency, not serialized


@pytest.mark.asyncio
async def test_run_batch_sequential_runs_one_at_a_time(repos, workspace, tool_service, version_service):
    connectors = ConnectorRegistry({"slow": SlowHandler(delay=0.02)})
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="slow")
    engine = make_engine(repos, connectors)
    parent, children = await engine.run_batch(tool.id, [{"i": 1}, {"i": 2}], execution_mode="sequential")
    assert parent.status == ExecutionStatus.SUCCEEDED.value
    assert len(children) == 2


@pytest.mark.asyncio
async def test_run_batch_reports_partial_failure(repos, workspace, tool_service, version_service):
    handler = FlakyHandler(fail_times=100)  # always fails
    connectors = ConnectorRegistry({"flaky": handler})
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="flaky", default_max_retries=0)
    engine = make_engine(repos, connectors)
    parent, children = await engine.run_batch(tool.id, [{"i": 1}, {"i": 2}], execution_mode="sequential")
    assert parent.status == ExecutionStatus.FAILED.value
    assert all(c.status == ExecutionStatus.FAILED.value for c in children)


@pytest.mark.asyncio
async def test_start_execution_requires_published_version(repos, workspace, tool_service):
    tool = await tool_service.create_tool(workspace.id, name="Unpublished", owner_id="u1", category="custom", organization_id="org-1")
    engine = make_engine(repos)
    with pytest.raises(ValidationError):
        await engine.start_execution(tool.id, input_data={})
