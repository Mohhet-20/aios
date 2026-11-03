from datetime import timedelta

import pytest

from tests.scheduler.conftest import make_published_tool
from tool_platform.core.exceptions import ValidationError
from tool_platform.database.base import utcnow
from tool_platform.domain.enums import ExecutionStatus, ScheduleStatus, ScheduleType
from tool_platform.scheduler.dispatcher import ScheduleDispatcher


@pytest.mark.asyncio
async def test_create_immediate_schedule_is_due_now(repos, workspace, tool_service, version_service, schedule_service):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    schedule = await schedule_service.create_immediate(tool.id, workspace.id, created_by="u1")
    assert schedule.schedule_type == ScheduleType.IMMEDIATE.value
    assert schedule.status == ScheduleStatus.ACTIVE.value
    due = await repos.schedules.list_due(as_of=utcnow() + timedelta(seconds=1))
    assert schedule.id in {s.id for s in due}


@pytest.mark.asyncio
async def test_create_cron_schedule_computes_next_run(repos, workspace, tool_service, version_service, schedule_service):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    schedule = await schedule_service.create_cron(tool.id, workspace.id, cron_expression="*/5 * * * *", created_by="u1")
    assert schedule.next_run_at is not None
    assert schedule.next_run_at > utcnow()


@pytest.mark.asyncio
async def test_invalid_cron_expression_rejected(workspace, tool_service, version_service, schedule_service):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    with pytest.raises(ValidationError):
        await schedule_service.create_cron(tool.id, workspace.id, cron_expression="not a cron", created_by="u1")


@pytest.mark.asyncio
async def test_dispatcher_fires_immediate_schedule_and_completes_it(repos, workspace, tool_service, version_service, schedule_service, engine):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    schedule = await schedule_service.create_immediate(tool.id, workspace.id, created_by="u1")

    dispatcher = ScheduleDispatcher(repos, engine)
    started = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=1))
    assert len(started) == 1
    assert started[0].status == ExecutionStatus.SUCCEEDED.value

    refreshed = await repos.schedules.get_or_404(schedule.id)
    assert refreshed.status == ScheduleStatus.COMPLETED.value
    assert refreshed.run_count == 1
    assert refreshed.last_execution_id == started[0].id

    started_again = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=2))
    assert started_again == []


@pytest.mark.asyncio
async def test_dispatcher_reschedules_recurring_schedule(repos, workspace, tool_service, version_service, schedule_service, engine):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    schedule = await schedule_service.create_recurring(tool.id, workspace.id, interval_seconds=300, created_by="u1")

    dispatcher = ScheduleDispatcher(repos, engine)
    as_of_1 = utcnow() + timedelta(seconds=1)
    started = await dispatcher.tick(as_of=as_of_1)
    assert len(started) == 1

    refreshed = await repos.schedules.get_or_404(schedule.id)
    assert refreshed.status == ScheduleStatus.ACTIVE.value
    assert refreshed.run_count == 1
    assert refreshed.next_run_at >= as_of_1 + timedelta(seconds=299)

    started_soon = await dispatcher.tick(as_of=as_of_1 + timedelta(seconds=5))
    assert started_soon == []

    started_later = await dispatcher.tick(as_of=as_of_1 + timedelta(seconds=301))
    assert len(started_later) == 1
    refreshed2 = await repos.schedules.get_or_404(schedule.id)
    assert refreshed2.run_count == 2


@pytest.mark.asyncio
async def test_dispatcher_respects_concurrency_limit(repos, workspace, tool_service, version_service, schedule_service, engine):
    from tool_platform.models.execution import ToolExecutionModel

    tool, version = await make_published_tool(tool_service, version_service, workspace)
    await repos.executions.add(ToolExecutionModel(
        tool_id=tool.id, tool_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, triggered_by="someone-else",
    ))

    schedule = await schedule_service.create_immediate(tool.id, workspace.id, created_by="u1")
    schedule.max_concurrent_executions = 1
    await repos.schedules.update(schedule)

    dispatcher = ScheduleDispatcher(repos, engine)
    started = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=1))
    assert started == []

    refreshed = await repos.schedules.get_or_404(schedule.id)
    assert refreshed.run_count == 0


@pytest.mark.asyncio
async def test_dispatcher_respects_rate_limit(repos, workspace, tool_service, version_service, schedule_service, engine):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    await schedule_service.create_recurring(tool.id, workspace.id, interval_seconds=1, created_by="u1", rate_limit_per_minute=1)

    dispatcher = ScheduleDispatcher(repos, engine)
    as_of = utcnow() + timedelta(seconds=1)
    first = await dispatcher.tick(as_of=as_of)
    assert len(first) == 1

    second = await dispatcher.tick(as_of=as_of + timedelta(seconds=2))
    assert second == []


@pytest.mark.asyncio
async def test_pause_prevents_dispatch_and_resume_restores_it(repos, workspace, tool_service, version_service, schedule_service, engine):
    tool, _version = await make_published_tool(tool_service, version_service, workspace)
    schedule = await schedule_service.create_immediate(tool.id, workspace.id, created_by="u1")
    await schedule_service.pause(schedule.id)

    dispatcher = ScheduleDispatcher(repos, engine)
    started = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=1))
    assert started == []

    await schedule_service.resume(schedule.id)
    started_after_resume = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=2))
    assert len(started_after_resume) == 1


@pytest.mark.asyncio
async def test_dispatcher_orders_by_priority(repos, workspace, tool_service, version_service, schedule_service, engine):
    tool_low, _v1 = await make_published_tool(tool_service, version_service, workspace, name="Low")
    tool_critical, _v2 = await make_published_tool(tool_service, version_service, workspace, name="Critical")

    await schedule_service.create_immediate(tool_low.id, workspace.id, created_by="u1", priority="low")
    await schedule_service.create_immediate(tool_critical.id, workspace.id, created_by="u1", priority="critical")

    dispatcher = ScheduleDispatcher(repos, engine)
    started = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=1))
    assert len(started) == 2
    assert started[0].tool_id == tool_critical.id
    assert started[1].tool_id == tool_low.id
