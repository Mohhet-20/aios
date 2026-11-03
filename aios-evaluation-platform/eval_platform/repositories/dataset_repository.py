from __future__ import annotations

from sqlalchemy import select

from eval_platform.models.dataset import DatasetItemModel, DatasetModel, DatasetVersionModel
from eval_platform.repositories.base import SQLAlchemyRepository


class DatasetRepository(SQLAlchemyRepository[DatasetModel]):
    model = DatasetModel

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None, dataset_type: str | None = None) -> list[DatasetModel]:
        stmt = select(DatasetModel).where(DatasetModel.workspace_id == workspace_id, DatasetModel.is_deleted.is_(False))
        if status:
            stmt = stmt.where(DatasetModel.status == status)
        if dataset_type:
            stmt = stmt.where(DatasetModel.dataset_type == dataset_type)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_slug(self, workspace_id: str, slug: str) -> DatasetModel | None:
        stmt = select(DatasetModel).where(DatasetModel.workspace_id == workspace_id, DatasetModel.slug == slug, DatasetModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()

    async def list_shared_with_workspace(self, workspace_id: str, organization_id: str) -> list[DatasetModel]:
        stmt = select(DatasetModel).where(DatasetModel.organization_id == organization_id, DatasetModel.is_deleted.is_(False))
        all_org_datasets = list((await self.session.execute(stmt)).scalars().all())
        return [d for d in all_org_datasets if workspace_id in (d.shared_with_workspace_ids or [])]


class DatasetVersionRepository(SQLAlchemyRepository[DatasetVersionModel]):
    model = DatasetVersionModel

    async def list_for_dataset(self, dataset_id: str) -> list[DatasetVersionModel]:
        stmt = select(DatasetVersionModel).where(DatasetVersionModel.dataset_id == dataset_id).order_by(DatasetVersionModel.version_number.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest_draft(self, dataset_id: str) -> DatasetVersionModel | None:
        stmt = select(DatasetVersionModel).where(
            DatasetVersionModel.dataset_id == dataset_id, DatasetVersionModel.status == "draft",
        ).order_by(DatasetVersionModel.version_number.desc())
        return (await self.session.execute(stmt)).scalars().first()

    async def get_max_version_number(self, dataset_id: str) -> int:
        stmt = select(DatasetVersionModel.version_number).where(DatasetVersionModel.dataset_id == dataset_id).order_by(DatasetVersionModel.version_number.desc())
        result = (await self.session.execute(stmt)).scalars().first()
        return result or 0


class DatasetItemRepository(SQLAlchemyRepository[DatasetItemModel]):
    model = DatasetItemModel

    async def list_for_version(self, dataset_version_id: str) -> list[DatasetItemModel]:
        stmt = select(DatasetItemModel).where(DatasetItemModel.dataset_version_id == dataset_version_id)
        return list((await self.session.execute(stmt)).scalars().all())
