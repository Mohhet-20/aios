"""ORM <-> domain-aggregate bridge for Schedule, mirroring the pattern
used for Workflow/Execution elsewhere in this platform."""
from __future__ import annotations

from workflow_platform.domain.entities import Schedule
from workflow_platform.domain.enums import ScheduleStatus
from workflow_platform.models.schedule import ScheduleModel


def schedule_to_domain(model: ScheduleModel) -> Schedule:
    return Schedule(
        id=model.id, workflow_id=model.workflow_id, workspace_id=model.workspace_id,
        schedule_type=model.schedule_type, created_by=model.created_by, status=ScheduleStatus(model.status),
        cron_expression=model.cron_expression, interval_seconds=model.interval_seconds, run_at=model.run_at,
        next_run_at=model.next_run_at, last_run_at=model.last_run_at, run_count=model.run_count,
    )


def apply_schedule_domain_to_model(entity: Schedule, model: ScheduleModel) -> None:
    model.status = entity.status.value
    model.next_run_at = entity.next_run_at
    model.last_run_at = entity.last_run_at
    model.run_count = entity.run_count
    model.is_active = entity.status == ScheduleStatus.ACTIVE
