"""ScheduleService: CRUD + lifecycle for `ToolScheduleModel` — the "when
does this tool run" side of the Task Scheduler. `ScheduleDispatcher` (in
`dispatcher.py`) is the "actually run it" side; this service only ever
creates rows and drives the `Schedule` domain entity's pause/resume/
cancel transitions, the same split `ToolService`/`ToolExecutionEngine`
use elsewhere in this platform."""
from __future__ import annotations

from datetime import datetime

from tool_platform.core.exceptions import ValidationError
from tool_platform.database.base import utcnow
from tool_platform.domain.enums import Priority, ScheduleType
from tool_platform.models.schedule import ToolScheduleModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.scheduler.cron import next_fire_time, validate_cron_expression
from tool_platform.scheduler.mappers import apply_schedule_domain_to_model, schedule_to_domain


class ScheduleService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_immediate(
        self, tool_id: str, workspace_id: str, *, created_by: str, input_data: dict | None = None,
        priority: str = Priority.NORMAL.value,
    ) -> ToolScheduleModel:
        return await self._create(
            tool_id, workspace_id, schedule_type=ScheduleType.IMMEDIATE.value, next_run_at=utcnow(),
            created_by=created_by, input_data=input_data, priority=priority,
        )

    async def create_delayed(
        self, tool_id: str, workspace_id: str, *, run_at: datetime, created_by: str,
        input_data: dict | None = None, priority: str = Priority.NORMAL.value,
    ) -> ToolScheduleModel:
        return await self._create(
            tool_id, workspace_id, schedule_type=ScheduleType.DELAYED.value, next_run_at=run_at, run_at=run_at,
            created_by=created_by, input_data=input_data, priority=priority,
        )

    async def create_calendar(
        self, tool_id: str, workspace_id: str, *, run_at: datetime, created_by: str,
        input_data: dict | None = None, priority: str = Priority.NORMAL.value,
    ) -> ToolScheduleModel:
        return await self._create(
            tool_id, workspace_id, schedule_type=ScheduleType.CALENDAR.value, next_run_at=run_at, run_at=run_at,
            created_by=created_by, input_data=input_data, priority=priority,
        )

    async def create_recurring(
        self, tool_id: str, workspace_id: str, *, interval_seconds: int, created_by: str,
        start_at: datetime | None = None, input_data: dict | None = None,
        priority: str = Priority.NORMAL.value, max_concurrent_executions: int | None = None,
        rate_limit_per_minute: int | None = None,
    ) -> ToolScheduleModel:
        if interval_seconds <= 0:
            raise ValidationError("interval_seconds must be positive for a recurring schedule")
        return await self._create(
            tool_id, workspace_id, schedule_type=ScheduleType.RECURRING.value,
            next_run_at=start_at or utcnow(), interval_seconds=interval_seconds, created_by=created_by,
            input_data=input_data, priority=priority, max_concurrent_executions=max_concurrent_executions,
            rate_limit_per_minute=rate_limit_per_minute,
        )

    async def create_cron(
        self, tool_id: str, workspace_id: str, *, cron_expression: str, created_by: str,
        input_data: dict | None = None, priority: str = Priority.NORMAL.value,
        max_concurrent_executions: int | None = None, rate_limit_per_minute: int | None = None,
    ) -> ToolScheduleModel:
        validate_cron_expression(cron_expression)
        return await self._create(
            tool_id, workspace_id, schedule_type=ScheduleType.CRON.value,
            next_run_at=next_fire_time(cron_expression, after=utcnow()), cron_expression=cron_expression,
            created_by=created_by, input_data=input_data, priority=priority,
            max_concurrent_executions=max_concurrent_executions, rate_limit_per_minute=rate_limit_per_minute,
        )

    async def _create(
        self, tool_id: str, workspace_id: str, *, schedule_type: str, next_run_at: datetime, created_by: str,
        input_data: dict | None = None, priority: str = Priority.NORMAL.value,
        cron_expression: str | None = None, interval_seconds: int | None = None, run_at: datetime | None = None,
        max_concurrent_executions: int | None = None, rate_limit_per_minute: int | None = None,
    ) -> ToolScheduleModel:
        return await self.repos.schedules.add(ToolScheduleModel(
            tool_id=tool_id, workspace_id=workspace_id, schedule_type=schedule_type, next_run_at=next_run_at,
            cron_expression=cron_expression, interval_seconds=interval_seconds, run_at=run_at, priority=priority,
            created_by=created_by, input_data=input_data or {},
            max_concurrent_executions=max_concurrent_executions, rate_limit_per_minute=rate_limit_per_minute,
        ))

    # -- lifecycle ----------------------------------------------------------------

    async def pause(self, schedule_id: str) -> ToolScheduleModel:
        return await self._apply_transition(schedule_id, "pause")

    async def resume(self, schedule_id: str) -> ToolScheduleModel:
        return await self._apply_transition(schedule_id, "resume")

    async def cancel(self, schedule_id: str) -> ToolScheduleModel:
        return await self._apply_transition(schedule_id, "cancel")

    async def _apply_transition(self, schedule_id: str, transition: str) -> ToolScheduleModel:
        model = await self.repos.schedules.get_or_404(schedule_id)
        entity = schedule_to_domain(model)
        getattr(entity, transition)()
        apply_schedule_domain_to_model(entity, model)
        return await self.repos.schedules.update(model)

    async def list_for_tool(self, tool_id: str) -> list[ToolScheduleModel]:
        return await self.repos.schedules.list_for_tool(tool_id)

    async def list_active_for_workspace(self, workspace_id: str) -> list[ToolScheduleModel]:
        return await self.repos.schedules.list_active_for_workspace(workspace_id)
