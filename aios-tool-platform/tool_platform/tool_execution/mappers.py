"""ORM <-> domain-aggregate bridge for ToolExecution."""
from __future__ import annotations

from tool_platform.domain.entities import ToolExecution
from tool_platform.domain.enums import ExecutionStatus
from tool_platform.models.execution import ToolExecutionModel


def execution_to_domain(model: ToolExecutionModel) -> ToolExecution:
    return ToolExecution(
        id=model.id, tool_id=model.tool_id, tool_version_id=model.tool_version_id, workspace_id=model.workspace_id,
        status=ExecutionStatus(model.status), attempt_number=model.attempt_number, max_retries=model.max_retries,
        input_data=dict(model.input_data or {}), output_data=dict(model.output_data or {}),
        error_message=model.error_message, started_at=model.started_at, completed_at=model.completed_at,
        duration_ms=model.duration_ms,
    )


def apply_execution_domain_to_model(entity: ToolExecution, model: ToolExecutionModel) -> None:
    model.status = entity.status.value
    model.attempt_number = entity.attempt_number
    model.output_data = entity.output_data
    model.error_message = entity.error_message
    model.started_at = entity.started_at
    model.completed_at = entity.completed_at
    model.duration_ms = entity.duration_ms
