"""ORM <-> domain-aggregate bridge for Execution and NodeExecution,
mirroring `workflow_core/mappers.py`'s pattern for Workflow."""
from __future__ import annotations

from workflow_platform.domain.entities import Execution, NodeExecution
from workflow_platform.domain.enums import ExecutionStatus, NodeExecutionStatus
from workflow_platform.models.execution import ExecutionModel, NodeExecutionModel


def execution_to_domain(model: ExecutionModel) -> Execution:
    return Execution(
        id=model.id, workflow_id=model.workflow_id, workflow_version_id=model.workflow_version_id,
        workspace_id=model.workspace_id, status=ExecutionStatus(model.status), priority=model.priority,
        trigger_type=model.trigger_type, triggered_by=model.triggered_by,
        input_variables=dict(model.input_variables or {}), output_variables=dict(model.output_variables or {}),
        context_variables=dict(model.context_variables or {}), current_node_key=model.current_node_key,
        parent_execution_id=model.parent_execution_id, recursion_depth=model.recursion_depth,
        error_message=model.error_message, started_at=model.started_at, completed_at=model.completed_at,
        timeout_at=model.timeout_at,
    )


def apply_execution_domain_to_model(entity: Execution, model: ExecutionModel) -> None:
    model.status = entity.status.value
    model.output_variables = entity.output_variables
    model.context_variables = entity.context_variables
    model.current_node_key = entity.current_node_key
    model.error_message = entity.error_message
    model.started_at = entity.started_at
    model.completed_at = entity.completed_at


def node_execution_to_domain(model: NodeExecutionModel) -> NodeExecution:
    return NodeExecution(
        id=model.id, execution_id=model.execution_id, node_key=model.node_key, node_type=model.node_type,
        status=NodeExecutionStatus(model.status), attempt_number=model.attempt_number,
        input_data=dict(model.input_data or {}), output_data=dict(model.output_data or {}),
        error_message=model.error_message, started_at=model.started_at, completed_at=model.completed_at,
        duration_ms=model.duration_ms,
    )


def apply_node_execution_domain_to_model(entity: NodeExecution, model: NodeExecutionModel) -> None:
    model.status = entity.status.value
    model.attempt_number = entity.attempt_number
    model.output_data = entity.output_data
    model.error_message = entity.error_message
    model.started_at = entity.started_at
    model.completed_at = entity.completed_at
    model.duration_ms = entity.duration_ms
