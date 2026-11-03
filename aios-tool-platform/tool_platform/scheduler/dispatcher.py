"""ScheduleDispatcher: the "actually run it" half of the Task Scheduler.
One `tick()` call polls every ACTIVE, due `ToolScheduleModel` row and
fires each one whose concurrency and rate-limit checks pass, via the
platform's own `ToolExecutionEngine.start_execution`. A real deployment
calls `tick()` on a timer — this class doesn't own that timer itself,
matching the same "coordinates, doesn't own" principle the Execution
Engine's docstring lays out for parallelism.

Rate limiting here is an in-memory sliding window scoped to *this*
dispatcher instance — correct for a single scheduler process, but not
shared across multiple dispatcher processes running for horizontal
scale; a production deployment with more than one dispatcher needs a
shared rate-limit store (Redis, or a DB-backed token count) instead,
and that swap is isolated to `_check_rate_limit`. Concurrency limits are
already safe under multiple dispatchers, since `count_active_for_tool`
reads the database's actual execution rows rather than in-memory
state."""
from __future__ import annotations

from datetime import datetime, timedelta

from tool_platform.database.base import utcnow
from tool_platform.domain.enums import ScheduleType
from tool_platform.models.execution import ToolExecutionModel
from tool_platform.models.schedule import ToolScheduleModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.scheduler.cron import next_fire_time
from tool_platform.scheduler.mappers import apply_schedule_domain_to_model, schedule_to_domain
from tool_platform.tool_execution.engine import ToolExecutionEngine

_PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2, "low": 3}


class ScheduleDispatcher:
    def __init__(self, repos: RepositoryRegistry, execution_engine: ToolExecutionEngine, *, rate_window_seconds: int = 60):
        self.repos = repos
        self.engine = execution_engine
        self._rate_window_seconds = rate_window_seconds
        self._recent_fires: dict[str, list[datetime]] = {}

    async def tick(self, *, as_of: datetime | None = None, limit: int = 100) -> list[ToolExecutionModel]:
        as_of = as_of or utcnow()
        due = await self.repos.schedules.list_due(as_of=as_of)
        due = sorted(due, key=lambda s: (_PRIORITY_RANK.get(s.priority, 2), s.next_run_at))

        started: list[ToolExecutionModel] = []
        for schedule in due[:limit]:
            if not await self._concurrency_allows(schedule):
                continue
            if not self._check_rate_limit(schedule, as_of):
                continue
            started.append(await self._fire(schedule, as_of))
        return started

    async def _concurrency_allows(self, schedule: ToolScheduleModel) -> bool:
        if schedule.max_concurrent_executions is None:
            return True
        active = await self.repos.executions.count_active_for_tool(schedule.tool_id)
        return active < schedule.max_concurrent_executions

    def _check_rate_limit(self, schedule: ToolScheduleModel, as_of: datetime) -> bool:
        if schedule.rate_limit_per_minute is None:
            return True
        history = self._recent_fires.setdefault(schedule.id, [])
        cutoff = as_of - timedelta(seconds=self._rate_window_seconds)
        history[:] = [t for t in history if t > cutoff]
        if len(history) >= schedule.rate_limit_per_minute:
            return False
        history.append(as_of)
        return True

    async def _fire(self, schedule: ToolScheduleModel, as_of: datetime) -> ToolExecutionModel:
        execution = await self.engine.start_execution(
            schedule.tool_id, triggered_by=schedule.created_by, trigger_type="schedule",
            input_data=dict(schedule.input_data), priority=schedule.priority,
        )

        entity = schedule_to_domain(schedule)
        entity.record_run(next_run_at=self._compute_next_run(schedule, as_of))
        apply_schedule_domain_to_model(entity, schedule)
        schedule.last_execution_id = execution.id
        await self.repos.schedules.update(schedule)
        return execution

    def _compute_next_run(self, schedule: ToolScheduleModel, as_of: datetime) -> datetime | None:
        if schedule.schedule_type == ScheduleType.RECURRING.value and schedule.interval_seconds:
            return as_of + timedelta(seconds=schedule.interval_seconds)
        if schedule.schedule_type == ScheduleType.CRON.value and schedule.cron_expression:
            return next_fire_time(schedule.cron_expression, after=as_of)
        return None  # IMMEDIATE / DELAYED / CALENDAR are one-shot — record_run() auto-completes them
