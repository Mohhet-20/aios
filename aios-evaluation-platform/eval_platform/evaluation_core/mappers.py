"""ORM <-> domain-aggregate bridge for Evaluation, mirroring every prior
AIOS platform's mappers.py pattern."""
from __future__ import annotations

from eval_platform.domain.entities import Evaluation
from eval_platform.domain.enums import EvaluationStatus
from eval_platform.models.evaluation import EvaluationModel


def evaluation_to_domain(model: EvaluationModel) -> Evaluation:
    return Evaluation(
        id=model.id, workspace_id=model.workspace_id, organization_id=model.organization_id, name=model.name,
        slug=model.slug, owner_id=model.owner_id, category=model.category, description=model.description,
        tags=list(model.tags or []), status=EvaluationStatus(model.status),
        current_version_id=model.current_version_id, eval_metadata=dict(model.eval_metadata or {}),
    )


def apply_evaluation_domain_to_model(entity: Evaluation, model: EvaluationModel) -> None:
    model.status = entity.status.value
    model.current_version_id = entity.current_version_id
    model.tags = entity.tags
    model.eval_metadata = entity.eval_metadata
