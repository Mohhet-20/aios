"""ORM <-> domain-aggregate mapping for Prompt/PromptVersion. Only the
versioning workflow (approval/promotion state machine) needs the full
domain aggregate — everything else in the platform reads/writes the ORM
models directly through repositories, same simplification the AIOS
backend (the core backend) documented for its own flagship aggregate.
"""
from __future__ import annotations

from prompt_platform.domain.entities import Prompt as PromptEntity
from prompt_platform.domain.entities import PromptVersion as PromptVersionEntity
from prompt_platform.domain.enums import PromptStatus, VersionBranch, VersionStatus
from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.version import PromptVersionModel


def version_to_domain(model: PromptVersionModel) -> PromptVersionEntity:
    return PromptVersionEntity(
        id=model.id,
        prompt_id=model.prompt_id,
        version_number=model.version_number,
        user_template=model.user_template,
        system_template=model.system_template,
        developer_template=model.developer_template,
        variables_schema=list(model.variables_schema or []),
        parameters=dict(model.parameters or {}),
        status=VersionStatus(model.status),
        branch=VersionBranch(model.branch),
        release_notes=model.release_notes,
        eval_score=model.eval_score,
        parent_version_id=model.parent_version_id,
        submitted_for_review_by=model.submitted_for_review_by,
        submitted_for_review_at=model.submitted_for_review_at,
        approved_by=model.approved_by,
        approved_at=model.approved_at,
        rejection_reason=model.rejection_reason,
    )


def apply_version_domain_to_model(entity: PromptVersionEntity, model: PromptVersionModel) -> PromptVersionModel:
    model.status = entity.status.value
    model.branch = entity.branch.value
    model.release_notes = entity.release_notes
    model.eval_score = entity.eval_score
    model.submitted_for_review_by = entity.submitted_for_review_by
    model.submitted_for_review_at = entity.submitted_for_review_at
    model.approved_by = entity.approved_by
    model.approved_at = entity.approved_at
    model.rejection_reason = entity.rejection_reason
    return model


def prompt_to_domain(model: PromptModel, version_models: list[PromptVersionModel]) -> PromptEntity:
    entity = PromptEntity(
        id=model.id,
        project_id=model.project_id,
        workspace_id=model.workspace_id,
        name=model.name,
        slug=model.slug,
        owner_id=model.owner_id,
        status=PromptStatus(model.status),
        latest_version_number=model.latest_version_number,
        production_version_id=model.production_version_id,
        stable_version_id=model.stable_version_id,
    )
    entity.versions = [version_to_domain(v) for v in version_models]
    return entity
