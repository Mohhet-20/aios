"""ORM <-> domain-aggregate bridge for Schedule, mirroring the pattern
used for Tool/ToolExecution elsewhere in this platform."""
from __future__ import annotations

from tool_platform.domain.entities import Schedule
from tool_platform.domain.enums import ScheduleStatus
from tool_platform.models.schedule import ToolScheduleModel


def schedule_to_domain(model: ToolScheduleModel) -> Schedule:
    return Schedule(
        id=model.id, tool_id=model.tool_id, workspace_id=model.workspace_id,
        schedule_type=model.schedule_type, created_by=model.created_by, status=ScheduleStatus(model.status),
        cron_expression=model.cron_expression, interval_seconds=model.interval_seconds, run_at=model.run_at,
        next_run_at=model.next_run_at, last_run_at=model.last_run_at, run_count=model.run_count,
    )


def apply_schedule_domain_to_model(entity: Schedule, model: ToolScheduleModel) -> None:
    model.status = entity.status.value
    model.next_run_at = entity.next_run_at
    model.last_run_at = entity.last_run_at
    model.run_count = entity.run_count
    model.is_active = entity.status == ScheduleStatus.ACTIVE
