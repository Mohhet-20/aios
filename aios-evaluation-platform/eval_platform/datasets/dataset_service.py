"""DatasetService: identity/ownership/lifecycle CRUD for the top-level
`DatasetModel` record. Editing the actual item set lives in
`version_service.py` — this service only ever touches identity fields
and drives the `Dataset` domain entity's lifecycle transitions,
mirroring evaluation_core's `EvaluationService`."""
from __future__ import annotations

from slugify import slugify

from eval_platform.core.exceptions import DatasetError
from eval_platform.core.pagination import Page, PaginationParams
from eval_platform.datasets.mappers import apply_dataset_domain_to_model, dataset_to_domain
from eval_platform.models.dataset import DatasetModel
from eval_platform.repositories.registry import RepositoryRegistry


class DatasetService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_dataset(
        self, workspace_id: str, *, name: str, owner_id: str, dataset_type: str, organization_id: str,
        slug: str | None = None, description: str | None = None, tags: list[str] | None = None,
        lineage_parent_dataset_id: str | None = None, dataset_metadata: dict | None = None,
    ) -> DatasetModel:
        resolved_slug = slug or slugify(name)
        existing = await self.repos.datasets.get_by_slug(workspace_id, resolved_slug)
        if existing is not None:
            raise DatasetError(f"a dataset with slug '{resolved_slug}' already exists in this workspace")

        return await self.repos.datasets.add(DatasetModel(
            workspace_id=workspace_id, organization_id=organization_id, name=name, slug=resolved_slug,
            description=description, owner_id=owner_id, dataset_type=dataset_type, tags=tags or [],
            lineage_parent_dataset_id=lineage_parent_dataset_id, dataset_metadata=dataset_metadata or {},
        ))

    async def get_dataset(self, dataset_id: str) -> DatasetModel:
        return await self.repos.datasets.get_or_404(dataset_id)

    async def list_datasets(
        self, workspace_id: str, params: PaginationParams, *, status: str | None = None, dataset_type: str | None = None
    ) -> Page[DatasetModel]:
        filters: dict = {"workspace_id": workspace_id}
        if status:
            filters["status"] = status
        if dataset_type:
            filters["dataset_type"] = dataset_type
        return await self.repos.datasets.paginated_list(params, filters=filters)

    async def list_shared_with_workspace(self, workspace_id: str, organization_id: str) -> list[DatasetModel]:
        return await self.repos.datasets.list_shared_with_workspace(workspace_id, organization_id)

    async def share_with_workspace(self, dataset_id: str, target_workspace_id: str) -> DatasetModel:
        dataset = await self.repos.datasets.get_or_404(dataset_id)
        shared = set(dataset.shared_with_workspace_ids or [])
        shared.add(target_workspace_id)
        dataset.shared_with_workspace_ids = sorted(shared)
        return await self.repos.datasets.update(dataset)

    async def update_dataset(self, dataset_id: str, **fields) -> DatasetModel:
        dataset = await self.repos.datasets.get_or_404(dataset_id)
        allowed = {"name", "description", "tags", "dataset_metadata"}
        unknown = set(fields) - allowed
        if unknown:
            raise DatasetError(f"cannot update fields: {sorted(unknown)}")
        for key, value in fields.items():
            setattr(dataset, key, value)
        return await self.repos.datasets.update(dataset)

    async def delete_dataset(self, dataset_id: str) -> None:
        dataset = await self.repos.datasets.get_or_404(dataset_id)
        await self.repos.datasets.delete(dataset)

    # -- lifecycle ------------------------------------------------------------

    async def publish(self, dataset_id: str, version_id: str) -> DatasetModel:
        return await self._apply_transition(dataset_id, "publish", version_id)

    async def republish(self, dataset_id: str, version_id: str) -> DatasetModel:
        return await self._apply_transition(dataset_id, "republish", version_id)

    async def archive(self, dataset_id: str) -> DatasetModel:
        model = await self.repos.datasets.get_or_404(dataset_id)
        entity = dataset_to_domain(model)
        entity.archive()
        apply_dataset_domain_to_model(entity, model)
        return await self.repos.datasets.update(model)

    async def _apply_transition(self, dataset_id: str, transition: str, version_id: str) -> DatasetModel:
        model = await self.repos.datasets.get_or_404(dataset_id)
        entity = dataset_to_domain(model)
        getattr(entity, transition)(version_id)
        apply_dataset_domain_to_model(entity, model)
        return await self.repos.datasets.update(model)
