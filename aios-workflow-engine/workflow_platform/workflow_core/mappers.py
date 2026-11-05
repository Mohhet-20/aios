"""ORM <-> domain-aggregate bridge for Workflow, mirroring every other
AIOS services's mappers.py pattern."""
from __future__ import annotations

from workflow_platform.domain.entities import Workflow
from workflow_platform.domain.enums import WorkflowStatus
from workflow_platform.models.workflow import WorkflowModel


def workflow_to_domain(model: WorkflowModel) -> Workflow:
    return Workflow(
        id=model.id, workspace_id=model.workspace_id, name=model.name, slug=model.slug, owner_id=model.owner_id,
        category=model.category, description=model.description, tags=list(model.tags or []),
        status=WorkflowStatus(model.status), priority=model.priority, current_version_id=model.current_version_id,
        variables=dict(model.variables or {}), workflow_metadata=dict(model.workflow_metadata or {}),
    )


def apply_workflow_domain_to_model(entity: Workflow, model: WorkflowModel) -> None:
    model.status = entity.status.value
    model.current_version_id = entity.current_version_id
    model.tags = entity.tags
    model.variables = entity.variables
    model.workflow_metadata = entity.workflow_metadata
