from __future__ import annotations

from sqlalchemy import select

from release_platform.models.artifact_distribution import (
    ArtifactModel,
    DistributionChannelModel,
    DistributionEntryModel,
)
from release_platform.repositories.base import SQLAlchemyRepository


class ArtifactRepository(SQLAlchemyRepository[ArtifactModel]):
    model = ArtifactModel

    async def list_for_release(self, tenant_id: str, release_id: str, *, artifact_type: str | None = None) -> list[ArtifactModel]:
        stmt = select(ArtifactModel).where(ArtifactModel.tenant_id == tenant_id, ArtifactModel.release_id == release_id)
        if artifact_type:
            stmt = stmt.where(ArtifactModel.artifact_type == artifact_type)
        return list((await self.session.execute(stmt)).scalars().all())


class DistributionChannelRepository(SQLAlchemyRepository[DistributionChannelModel]):
    model = DistributionChannelModel

    async def get_by_name(self, tenant_id: str, name: str) -> DistributionChannelModel | None:
        stmt = select(DistributionChannelModel).where(
            DistributionChannelModel.tenant_id == tenant_id, DistributionChannelModel.name == name,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, channel_type: str | None = None) -> list[DistributionChannelModel]:
        stmt = select(DistributionChannelModel).where(DistributionChannelModel.tenant_id == tenant_id)
        if channel_type:
            stmt = stmt.where(DistributionChannelModel.channel_type == channel_type)
        return list((await self.session.execute(stmt)).scalars().all())


class DistributionEntryRepository(SQLAlchemyRepository[DistributionEntryModel]):
    model = DistributionEntryModel

    async def list_for_artifact(self, tenant_id: str, artifact_id: str) -> list[DistributionEntryModel]:
        stmt = select(DistributionEntryModel).where(
            DistributionEntryModel.tenant_id == tenant_id, DistributionEntryModel.artifact_id == artifact_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())
