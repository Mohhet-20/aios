"""SchedulerDispatcher: the "actually run it" half of the Task
Scheduler. One `tick()` call polls every ACTIVE, due `ScheduleModel` row
and fires each one whose dependency, concurrency, and rate-limit checks
pass, via the platform's own `ExecutionEngine.start_execution`. A real
deployment calls `tick()` on a timer (a cron-style loop, or this
platform's own eventual host-process heartbeat) — this class doesn't
own that timer itself, matching the same "coordinates, doesn't own"
principle the Execution Engine's docstring lays out for parallelism.

Rate limiting here is an in-memory sliding window scoped to *this*
dispatcher instance — correct for a single scheduler process, but not
shared across multiple dispatcher processes running for horizontal
scale. A production deployment with more than one dispatcher needs a
shared rate-limit store (Redis, or a DB-backed token count) instead;
that swap is isolated to `_check_rate_limit`, not the rest of this
class. Concurrency limits, by contrast, are already safe under multiple
dispatchers, since `count_active_for_workflow` reads the database's
actual execution rows rather than in-memory state.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from workflow_platform.database.base import utcnow
from workflow_platform.domain.enums import ExecutionStatus, ScheduleType
from workflow_platform.models.execution import ExecutionModel
from workflow_platform.models.schedule import ScheduleModel
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.scheduler.cron import next_fire_time
from workflow_platform.scheduler.mappers import apply_schedule_domain_to_model, schedule_to_domain
from workflow_platform.workflow_engine.engine import ExecutionEngine

_PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2, "low": 3}


class SchedulerDispatcher:
    def __init__(self, repos: RepositoryRegistry, execution_engine: ExecutionEngine, *, rate_window_seconds: int = 60):
        self.repos = repos
        self.engine = execution_engine
        self._rate_window_seconds = rate_window_seconds
        self._recent_fires: dict[str, list[datetime]] = {}

    async def tick(self, *, as_of: datetime | None = None, limit: int = 100) -> list[ExecutionModel]:
        as_of = as_of or utcnow()
        due = await self.repos.schedules.list_due(as_of=as_of)

        eligible: list[ScheduleModel] = []
        for schedule in due:
            if await self._dependency_satisfied(schedule):
                eligible.append(schedule)
        eligible.sort(key=lambda s: (_PRIORITY_RANK.get(s.priority, 2), s.next_run_at))

        started: list[ExecutionModel] = []
        for schedule in eligible[:limit]:
            if not await self._concurrency_allows(schedule):
                continue
            if not self._check_rate_limit(schedule, as_of):
                continue
            started.append(await self._fire(schedule, as_of))
        return started

    async def _dependency_satisfied(self, schedule: ScheduleModel) -> bool:
        if not schedule.depends_on_schedule_id:
            return True
        dependency = await self.repos.schedules.get(schedule.depends_on_schedule_id)
        if dependency is None or not dependency.last_execution_id:
            return False
        dep_execution = await self.repos.executions.get(dependency.last_execution_id)
        if dep_execution is None or dep_execution.status != ExecutionStatus.COMPLETED.value:
            return False
        if schedule.last_run_at and dep_execution.completed_at and dep_execution.completed_at <= schedule.last_run_at:
            return False  # this dependency's successful run has already been consumed
        return True

    async def _concurrency_allows(self, schedule: ScheduleModel) -> bool:
        if schedule.max_concurrent_executions is None:
            return True
        active = await self.repos.executions.count_active_for_workflow(schedule.workflow_id)
        return active < schedule.max_concurrent_executions

    def _check_rate_limit(self, schedule: ScheduleModel, as_of: datetime) -> bool:
        if schedule.rate_limit_per_minute is None:
            return True
        history = self._recent_fires.setdefault(schedule.id, [])
        cutoff = as_of - timedelta(seconds=self._rate_window_seconds)
        history[:] = [t for t in history if t > cutoff]
        if len(history) >= schedule.rate_limit_per_minute:
            return False
        history.append(as_of)
        return True

    async def _fire(self, schedule: ScheduleModel, as_of: datetime) -> ExecutionModel:
        execution = await self.engine.start_execution(
            schedule.workflow_id, triggered_by=schedule.created_by, trigger_type="schedule",
            input_variables=dict(schedule.input_variables), priority=schedule.priority,
        )

        entity = schedule_to_domain(schedule)
        entity.record_run(next_run_at=self._compute_next_run(schedule, as_of))
        apply_schedule_domain_to_model(entity, schedule)
        schedule.last_execution_id = execution.id
        await self.repos.schedules.update(schedule)
        return execution

    def _compute_next_run(self, schedule: ScheduleModel, as_of: datetime) -> datetime | None:
        if schedule.schedule_type == ScheduleType.RECURRING.value and schedule.interval_seconds:
            return as_of + timedelta(seconds=schedule.interval_seconds)
        if schedule.schedule_type == ScheduleType.CRON.value and schedule.cron_expression:
            return next_fire_time(schedule.cron_expression, after=as_of)
        return None  # IMMEDIATE / DELAYED / CALENDAR are one-shot — record_run() auto-completes them
