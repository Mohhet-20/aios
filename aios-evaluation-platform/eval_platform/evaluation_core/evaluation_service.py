"""EvaluationService: identity/ownership/lifecycle CRUD for the
top-level `EvaluationModel` record. Editing the actual contract
(dataset binding/metrics/scoring config/pass threshold/target) lives in
`version_service.py` — this service only ever touches identity fields
and drives the `Evaluation` domain entity's lifecycle transitions."""
from __future__ import annotations

from slugify import slugify

from eval_platform.core.exceptions import ValidationError
from eval_platform.core.pagination import Page, PaginationParams
from eval_platform.evaluation_core.mappers import apply_evaluation_domain_to_model, evaluation_to_domain
from eval_platform.models.evaluation import EvaluationModel
from eval_platform.repositories.registry import RepositoryRegistry


class EvaluationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_evaluation(
        self, workspace_id: str, *, name: str, owner_id: str, category: str, organization_id: str,
        slug: str | None = None, description: str | None = None, tags: list[str] | None = None,
        eval_metadata: dict | None = None,
    ) -> EvaluationModel:
        resolved_slug = slug or slugify(name)
        existing = await self.repos.evaluations.get_by_slug(workspace_id, resolved_slug)
        if existing is not None:
            raise ValidationError(f"an evaluation with slug '{resolved_slug}' already exists in this workspace")

        return await self.repos.evaluations.add(EvaluationModel(
            workspace_id=workspace_id, organization_id=organization_id, name=name, slug=resolved_slug,
            description=description, owner_id=owner_id, category=category, tags=tags or [],
            eval_metadata=eval_metadata or {},
        ))

    async def get_evaluation(self, evaluation_id: str) -> EvaluationModel:
        return await self.repos.evaluations.get_or_404(evaluation_id)

    async def list_evaluations(
        self, workspace_id: str, params: PaginationParams, *, status: str | None = None, category: str | None = None
    ) -> Page[EvaluationModel]:
        filters: dict = {"workspace_id": workspace_id}
        if status:
            filters["status"] = status
        if category:
            filters["category"] = category
        return await self.repos.evaluations.paginated_list(params, filters=filters)

    async def search_evaluations(self, workspace_id: str, query: str) -> list[EvaluationModel]:
        return await self.repos.evaluations.search(workspace_id, query)

    async def update_evaluation(self, evaluation_id: str, **fields) -> EvaluationModel:
        evaluation = await self.repos.evaluations.get_or_404(evaluation_id)
        allowed = {"name", "description", "tags", "category", "eval_metadata"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValidationError(f"cannot update fields: {sorted(unknown)}")
        for key, value in fields.items():
            setattr(evaluation, key, value)
        return await self.repos.evaluations.update(evaluation)

    async def delete_evaluation(self, evaluation_id: str) -> None:
        evaluation = await self.repos.evaluations.get_or_404(evaluation_id)
        await self.repos.evaluations.delete(evaluation)

    # -- lifecycle ------------------------------------------------------------

    async def activate(self, evaluation_id: str, version_id: str) -> EvaluationModel:
        model = await self.repos.evaluations.get_or_404(evaluation_id)
        entity = evaluation_to_domain(model)
        entity.activate(version_id)
        apply_evaluation_domain_to_model(entity, model)
        return await self.repos.evaluations.update(model)

    async def deprecate(self, evaluation_id: str) -> EvaluationModel:
        return await self._apply_transition(evaluation_id, "deprecate")

    async def archive(self, evaluation_id: str) -> EvaluationModel:
        return await self._apply_transition(evaluation_id, "archive")

    async def _apply_transition(self, evaluation_id: str, transition: str) -> EvaluationModel:
        model = await self.repos.evaluations.get_or_404(evaluation_id)
        entity = evaluation_to_domain(model)
        getattr(entity, transition)()
        apply_evaluation_domain_to_model(entity, model)
        return await self.repos.evaluations.update(model)
