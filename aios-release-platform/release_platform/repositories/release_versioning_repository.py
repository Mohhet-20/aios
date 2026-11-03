from __future__ import annotations

from sqlalchemy import select

from release_platform.models.release_versioning import CompatibilityEntryModel, ReleaseModel, VersionHistoryModel
from release_platform.repositories.base import SQLAlchemyRepository


class ReleaseRepository(SQLAlchemyRepository[ReleaseModel]):
    model = ReleaseModel

    async def get_by_version(self, tenant_id: str, version: str) -> ReleaseModel | None:
        stmt = select(ReleaseModel).where(
            ReleaseModel.tenant_id == tenant_id, ReleaseModel.version == version, ReleaseModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, channel: str | None = None, status: str | None = None) -> list[ReleaseModel]:
        stmt = select(ReleaseModel).where(ReleaseModel.tenant_id == tenant_id, ReleaseModel.is_deleted.is_(False))
        if channel:
            stmt = stmt.where(ReleaseModel.channel == channel)
        if status:
            stmt = stmt.where(ReleaseModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())


class VersionHistoryRepository(SQLAlchemyRepository[VersionHistoryModel]):
    model = VersionHistoryModel

    async def list_for_release(self, tenant_id: str, release_id: str) -> list[VersionHistoryModel]:
        stmt = select(VersionHistoryModel).where(
            VersionHistoryModel.tenant_id == tenant_id, VersionHistoryModel.release_id == release_id,
        ).order_by(VersionHistoryModel.recorded_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())


class CompatibilityEntryRepository(SQLAlchemyRepository[CompatibilityEntryModel]):
    model = CompatibilityEntryModel

    async def list_for_version(self, tenant_id: str, version: str) -> list[CompatibilityEntryModel]:
        stmt = select(CompatibilityEntryModel).where(
            CompatibilityEntryModel.tenant_id == tenant_id, CompatibilityEntryModel.version == version,
        )
        return list((await self.session.execute(stmt)).scalars().all())
