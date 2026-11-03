"""ORM <-> domain-aggregate bridge for Task."""
from __future__ import annotations

from agent_platform.domain.entities import Task
from agent_platform.domain.enums import TaskPriority, TaskStatus
from agent_platform.models.task import TaskModel


def task_to_domain(model: TaskModel) -> Task:
    return Task(
        id=model.id, workspace_id=model.workspace_id, title=model.title, goal=model.goal, created_by=model.created_by,
        parent_task_id=model.parent_task_id, root_task_id=model.root_task_id, depth=model.depth,
        status=TaskStatus(model.status), priority=TaskPriority(model.priority), assigned_agent_id=model.assigned_agent_id,
        context=dict(model.context or {}), result=model.result, confidence=model.confidence,
        progress_percent=model.progress_percent, retry_count=model.retry_count, failure_reason=model.failure_reason,
    )


def apply_task_domain_to_model(entity: Task, model: TaskModel) -> None:
    model.status = entity.status.value
    model.priority = entity.priority.value
    model.assigned_agent_id = entity.assigned_agent_id
    model.context = entity.context
    model.result = entity.result
    model.confidence = entity.confidence
    model.progress_percent = entity.progress_percent
    model.retry_count = entity.retry_count
    model.failure_reason = entity.failure_reason
