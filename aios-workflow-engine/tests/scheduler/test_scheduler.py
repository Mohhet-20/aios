from datetime import timedelta

import pytest

from tests.scheduler.conftest import make_trivial_workflow
from workflow_platform.core.exceptions import ValidationError
from workflow_platform.database.base import utcnow
from workflow_platform.domain.enums import ExecutionStatus, ScheduleStatus, ScheduleType
from workflow_platform.scheduler.dispatcher import SchedulerDispatcher


@pytest.mark.asyncio
async def test_create_immediate_schedule_is_due_now(repos, workspace, workflow_service, version_service, schedule_service):
    wf = await make_trivial_workflow(workflow_service, version_service, workspace)
    schedule = await schedule_service.create_immediate(wf.id, workspace.id, created_by="u1")
    assert schedule.schedule_type == ScheduleType.IMMEDIATE.value
    assert schedule.status == ScheduleStatus.ACTIVE.value
    due = await repos.schedules.list_due(as_of=utcnow() + timedelta(seconds=1))
    assert schedule.id in {s.id for s in due}


@pytest.mark.asyncio
async def test_create_cron_schedule_computes_next_run(repos, workspace, workflow_service, version_service, schedule_service):
    wf = await make_trivial_workflow(workflow_service, version_service, workspace)
    schedule = await schedule_service.create_cron(wf.id, workspace.id, cron_expression="*/5 * * * *", created_by="u1")
    assert schedule.next_run_at is not None
    assert schedule.next_run_at > utcnow()


@pytest.mark.asyncio
async def test_invalid_cron_expression_rejected(workspace, workflow_service, version_service, schedule_service):
    wf = await make_trivial_workflow(workflow_service, version_service, workspace)
    with pytest.raises(ValidationError):
        await schedule_service.create_cron(wf.id, workspace.id, cron_expression="not a cron", created_by="u1")


@pytest.mark.asyncio
async def test_dispatcher_fires_immediate_schedule_and_completes_it(repos, workspace, workflow_service, version_service, schedule_service, engine):
    wf = await make_trivial_workflow(workflow_service, version_service, workspace)
    schedule = await schedule_service.create_immediate(wf.id, workspace.id, created_by="u1")

    dispatcher = SchedulerDispatcher(repos, engine)
    started = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=1))
    assert len(started) == 1
    assert started[0].status == ExecutionStatus.COMPLETED.value

    refreshed = await repos.schedules.get_or_404(schedule.id)
    assert refreshed.status == ScheduleStatus.COMPLETED.value  # one-shot: auto-completes after firing
    assert refreshed.run_count == 1
    assert refreshed.last_execution_id == started[0].id

    # a second tick should not re-fire a completed one-shot schedule
    started_again = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=2))
    assert started_again == []


@pytest.mark.asyncio
async def test_dispatcher_reschedules_recurring_schedule(repos, workspace, workflow_service, version_service, schedule_service, engine):
    wf = await make_trivial_workflow(workflow_service, version_service, workspace)
    schedule = await schedule_service.create_recurring(wf.id, workspace.id, interval_seconds=300, created_by="u1")

    dispatcher = SchedulerDispatcher(repos, engine)
    as_of_1 = utcnow() + timedelta(seconds=1)
    started = await dispatcher.tick(as_of=as_of_1)
    assert len(started) == 1

    refreshed = await repos.schedules.get_or_404(schedule.id)
    assert refreshed.status == ScheduleStatus.ACTIVE.value  # recurring stays active
    assert refreshed.run_count == 1
    assert refreshed.next_run_at >= as_of_1 + timedelta(seconds=299)

    # not due yet at as_of_1 + a few seconds
    started_soon = await dispatcher.tick(as_of=as_of_1 + timedelta(seconds=5))
    assert started_soon == []

    # due again once the interval has elapsed
    started_later = await dispatcher.tick(as_of=as_of_1 + timedelta(seconds=301))
    assert len(started_later) == 1
    refreshed2 = await repos.schedules.get_or_404(schedule.id)
    assert refreshed2.run_count == 2


@pytest.mark.asyncio
async def test_dispatcher_respects_concurrency_limit(repos, workspace, workflow_service, version_service, schedule_service, engine):
    """A schedule capped at max_concurrent_executions=0 effective active
    executions should never fire while that many are already active. We
    simulate "already at capacity" by pre-seeding an active execution for
    the same workflow directly."""
    from workflow_platform.models.execution import ExecutionModel

    wf = await make_trivial_workflow(workflow_service, version_service, workspace)
    version = (await repos.workflow_versions.list_for_workflow(wf.id))[0]
    await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, triggered_by="someone-else",
    ))

    schedule = await schedule_service.create_immediate(wf.id, workspace.id, created_by="u1")
    schedule.max_concurrent_executions = 1
    await repos.schedules.update(schedule)

    dispatcher = SchedulerDispatcher(repos, engine)
    started = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=1))
    assert started == []  # blocked: one RUNNING execution already occupies the only slot

    refreshed = await repos.schedules.get_or_404(schedule.id)
    assert refreshed.run_count == 0  # never fired, so never consumed its one-shot


@pytest.mark.asyncio
async def test_dispatcher_respects_rate_limit(repos, workspace, workflow_service, version_service, schedule_service, engine):
    wf = await make_trivial_workflow(workflow_service, version_service, workspace)
    await schedule_service.create_recurring(wf.id, workspace.id, interval_seconds=1, created_by="u1", rate_limit_per_minute=1)

    dispatcher = SchedulerDispatcher(repos, engine)
    as_of = utcnow() + timedelta(seconds=1)
    first = await dispatcher.tick(as_of=as_of)
    assert len(first) == 1

    # immediately due again (interval_seconds=1) but rate-limited to 1/min
    second = await dispatcher.tick(as_of=as_of + timedelta(seconds=2))
    assert second == []


@pytest.mark.asyncio
async def test_dependency_scheduling_waits_for_upstream_completion(repos, workspace, workflow_service, version_service, schedule_service, engine):
    wf_a = await make_trivial_workflow(workflow_service, version_service, workspace, name="Upstream")
    wf_b = await make_trivial_workflow(workflow_service, version_service, workspace, name="Downstream")

    schedule_a = await schedule_service.create_immediate(wf_a.id, workspace.id, created_by="u1")
    schedule_b = await schedule_service.create_immediate(wf_b.id, workspace.id, created_by="u1")
    await schedule_service.set_dependency(schedule_b.id, schedule_a.id)

    dispatcher = SchedulerDispatcher(repos, engine)
    as_of = utcnow() + timedelta(seconds=1)

    # first tick: A fires (immediate, no dependency); B is still blocked
    # because A hasn't recorded a completed execution as of *this* tick's
    # dependency check (A's last_execution_id is set only after A fires).
    started = await dispatcher.tick(as_of=as_of)
    fired_workflow_ids = {e.workflow_id for e in started}
    assert wf_a.id in fired_workflow_ids
    assert wf_b.id not in fired_workflow_ids

    # second tick: A has completed, so B is now eligible
    started_2 = await dispatcher.tick(as_of=as_of + timedelta(seconds=1))
    assert wf_b.id in {e.workflow_id for e in started_2}


@pytest.mark.asyncio
async def test_pause_prevents_dispatch_and_resume_restores_it(repos, workspace, workflow_service, version_service, schedule_service, engine):
    wf = await make_trivial_workflow(workflow_service, version_service, workspace)
    schedule = await schedule_service.create_immediate(wf.id, workspace.id, created_by="u1")
    await schedule_service.pause(schedule.id)

    dispatcher = SchedulerDispatcher(repos, engine)
    started = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=1))
    assert started == []

    await schedule_service.resume(schedule.id)
    started_after_resume = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=2))
    assert len(started_after_resume) == 1


@pytest.mark.asyncio
async def test_dispatcher_orders_by_priority(repos, workspace, workflow_service, version_service, schedule_service, engine):
    wf_low = await make_trivial_workflow(workflow_service, version_service, workspace, name="Low")
    wf_critical = await make_trivial_workflow(workflow_service, version_service, workspace, name="Critical")

    await schedule_service.create_immediate(wf_low.id, workspace.id, created_by="u1", priority="low")
    await schedule_service.create_immediate(wf_critical.id, workspace.id, created_by="u1", priority="critical")

    dispatcher = SchedulerDispatcher(repos, engine)
    started = await dispatcher.tick(as_of=utcnow() + timedelta(seconds=1))
    assert len(started) == 2
    assert started[0].workflow_id == wf_critical.id
    assert started[1].workflow_id == wf_low.id
