"""EvaluationVersionService: manages the versioned evaluation *contract*
— which dataset it runs against, which metrics it computes, per-metric
scoring weights, the pass threshold, and what's actually being
evaluated (`target_config`). Editing always creates or updates a DRAFT
version; a PUBLISHED version is immutable, so an in-flight
`EvaluationRun` that captured `evaluation_version_id` at start time
keeps scoring against the exact contract it started with even if a
newer version gets published mid-flight — the same reasoning as the
Tool Platform's ToolVersionService."""
from __future__ import annotations

from eval_platform.core.exceptions import ValidationError
from eval_platform.evaluation_core.evaluation_service import EvaluationService
from eval_platform.models.evaluation import EvaluationVersionModel
from eval_platform.repositories.registry import RepositoryRegistry

_DRAFT_EDITABLE_FIELDS = {
    "dataset_id", "metric_keys", "scoring_config", "pass_threshold", "target_config", "change_note",
}


class EvaluationVersionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.evaluations = EvaluationService(repos)

    async def get_or_create_draft(self, evaluation_id: str, *, created_by: str) -> EvaluationVersionModel:
        """Returns the existing draft version for this evaluation, or
        creates a new one seeded from the current active version's
        contract (or empty defaults, if this is the evaluation's first
        version ever)."""
        draft = await self.repos.evaluation_versions.get_latest_draft(evaluation_id)
        if draft is not None:
            return draft

        next_number = await self.repos.evaluation_versions.get_max_version_number(evaluation_id) + 1
        seed: dict = {}
        evaluation = await self.repos.evaluations.get_or_404(evaluation_id)
        if evaluation.current_version_id:
            source = await self.repos.evaluation_versions.get_or_404(evaluation.current_version_id)
            seed = {
                "dataset_id": source.dataset_id, "metric_keys": list(source.metric_keys or []),
                "scoring_config": dict(source.scoring_config or {}), "pass_threshold": source.pass_threshold,
                "target_config": dict(source.target_config or {}),
            }

        return await self.repos.evaluation_versions.add(EvaluationVersionModel(
            evaluation_id=evaluation_id, version_number=next_number, status="draft", created_by=created_by, **seed,
        ))

    async def list_versions(self, evaluation_id: str) -> list[EvaluationVersionModel]:
        return await self.repos.evaluation_versions.list_for_evaluation(evaluation_id)

    async def get_version(self, version_id: str) -> EvaluationVersionModel:
        return await self.repos.evaluation_versions.get_or_404(version_id)

    async def _require_draft(self, version_id: str) -> EvaluationVersionModel:
        version = await self.repos.evaluation_versions.get_or_404(version_id)
        if version.status != "draft":
            raise ValidationError(f"evaluation version '{version_id}' is {version.status}, not draft — cannot edit")
        return version

    async def update_draft(self, version_id: str, **fields) -> EvaluationVersionModel:
        version = await self._require_draft(version_id)
        unknown = set(fields) - _DRAFT_EDITABLE_FIELDS
        if unknown:
            raise ValidationError(f"cannot update fields: {sorted(unknown)}")
        for key, value in fields.items():
            setattr(version, key, value)
        return await self.repos.evaluation_versions.update(version)

    # -- publishing --------------------------------------------------------------

    async def publish_version(self, version_id: str, *, activate_evaluation: bool = True) -> EvaluationVersionModel:
        version = await self._require_draft(version_id)
        self._validate_contract(version)

        version.status = "published"
        version = await self.repos.evaluation_versions.update(version)

        if activate_evaluation:
            await self.evaluations.activate(version.evaluation_id, version.id)

        return version

    def _validate_contract(self, version: EvaluationVersionModel) -> None:
        if not version.metric_keys:
            raise ValidationError(f"evaluation version '{version.id}' must declare at least one metric to publish")
        if not version.target_config or "type" not in version.target_config:
            raise ValidationError(f"evaluation version '{version.id}' must declare a target_config with a 'type' to publish")
        if version.pass_threshold is not None and not (0.0 <= version.pass_threshold <= 1.0):
            raise ValidationError(f"evaluation version '{version.id}' pass_threshold must be between 0.0 and 1.0")

    async def deprecate_version(self, version_id: str) -> EvaluationVersionModel:
        version = await self.repos.evaluation_versions.get_or_404(version_id)
        if version.status != "published":
            raise ValidationError(f"only a published version can be deprecated (status: {version.status})")
        version.status = "deprecated"
        return await self.repos.evaluation_versions.update(version)
