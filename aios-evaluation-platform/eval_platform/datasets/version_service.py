"""DatasetVersionService: manages the versioned *snapshot* of items a
dataset holds. Appending items always creates or updates a DRAFT
version; a PUBLISHED version is immutable, so an `EvaluationRun` that
pinned a `dataset_id`'s items at start time stays reproducible even if
more items get appended later — the same reasoning as
`EvaluationVersionService`. Creating a new draft on top of an
already-published dataset copies the prior version's items forward so
appends are incremental, not a full re-entry."""
from __future__ import annotations

from sqlalchemy import update

from eval_platform.config.settings import get_settings
from eval_platform.core.exceptions import DatasetError, DatasetVersionError
from eval_platform.datasets.dataset_service import DatasetService
from eval_platform.models.dataset import DatasetItemModel, DatasetVersionModel
from eval_platform.repositories.registry import RepositoryRegistry


class DatasetVersionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.datasets = DatasetService(repos)

    async def get_or_create_draft(self, dataset_id: str, *, created_by: str) -> DatasetVersionModel:
        draft = await self.repos.dataset_versions.get_latest_draft(dataset_id)
        if draft is not None:
            return draft

        next_number = await self.repos.dataset_versions.get_max_version_number(dataset_id) + 1
        new_version = await self.repos.dataset_versions.add(DatasetVersionModel(
            dataset_id=dataset_id, version_number=next_number, status="draft", created_by=created_by,
        ))

        dataset = await self.repos.datasets.get_or_404(dataset_id)
        if dataset.current_version_id:
            source_items = await self.repos.dataset_items.list_for_version(dataset.current_version_id)
            for item in source_items:
                await self.repos.dataset_items.add(DatasetItemModel(
                    dataset_version_id=new_version.id, input_data=dict(item.input_data or {}),
                    expected_output=dict(item.expected_output or {}), item_metadata=dict(item.item_metadata or {}),
                ))
            new_version.item_count = len(source_items)
            new_version = await self.repos.dataset_versions.update(new_version)

        return new_version

    async def list_versions(self, dataset_id: str) -> list[DatasetVersionModel]:
        return await self.repos.dataset_versions.list_for_dataset(dataset_id)

    async def get_version(self, version_id: str) -> DatasetVersionModel:
        return await self.repos.dataset_versions.get_or_404(version_id)

    async def _require_draft(self, version_id: str) -> DatasetVersionModel:
        version = await self.repos.dataset_versions.get_or_404(version_id)
        if version.status != "draft":
            raise DatasetVersionError(f"dataset version '{version_id}' is {version.status}, not draft — cannot edit")
        return version

    # -- items ------------------------------------------------------------------

    async def add_items(self, version_id: str, items: list[dict]) -> DatasetVersionModel:
        version = await self._require_draft(version_id)
        if not items:
            raise DatasetError("cannot append an empty item batch")
        settings = get_settings()
        if len(items) > settings.max_dataset_batch_size:
            raise DatasetError(
                f"batch of {len(items)} items exceeds max_dataset_batch_size ({settings.max_dataset_batch_size})"
            )

        for item in items:
            await self.repos.dataset_items.add(DatasetItemModel(
                dataset_version_id=version.id, input_data=item.get("input_data", {}),
                expected_output=item.get("expected_output", {}), item_metadata=item.get("item_metadata", {}),
            ))

        # A plain `version.item_count += len(items)` is a read-modify-write
        # race: two concurrent sessions appending to the same draft can
        # both read the same starting count and each write their own
        # total, silently losing one side's update (caught by
        # tests/performance/test_concurrency.py). An atomic SQL-level
        # increment is safe under SQLite's single-writer-at-a-time model
        # because the UPDATE re-reads the current row value at the moment
        # it actually executes, not at the moment this Python code read it.
        await self.repos.session.execute(
            update(DatasetVersionModel).where(DatasetVersionModel.id == version.id).values(item_count=DatasetVersionModel.item_count + len(items))
        )
        await self.repos.session.flush()
        return await self.repos.dataset_versions.get_or_404(version.id)

    async def list_items(self, version_id: str) -> list[DatasetItemModel]:
        return await self.repos.dataset_items.list_for_version(version_id)

    # -- publishing --------------------------------------------------------------

    async def publish_version(self, version_id: str, *, change_note: str | None = None) -> DatasetVersionModel:
        version = await self._require_draft(version_id)
        if version.item_count <= 0:
            raise DatasetVersionError(f"dataset version '{version_id}' has no items — cannot publish an empty dataset")

        if change_note is not None:
            version.change_note = change_note
        version.status = "published"
        version = await self.repos.dataset_versions.update(version)

        dataset = await self.repos.datasets.get_or_404(version.dataset_id)
        if dataset.status == "published":
            await self.datasets.republish(dataset.id, version.id)
        else:
            await self.datasets.publish(dataset.id, version.id)

        return version

    async def deprecate_version(self, version_id: str) -> DatasetVersionModel:
        version = await self.repos.dataset_versions.get_or_404(version_id)
        if version.status != "published":
            raise DatasetVersionError(f"only a published version can be deprecated (status: {version.status})")
        version.status = "deprecated"
        return await self.repos.dataset_versions.update(version)
