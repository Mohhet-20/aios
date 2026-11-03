from __future__ import annotations

from sqlalchemy import select

from release_platform.models.feature_flag import FeatureFlagModel, FeatureFlagOverrideModel
from release_platform.repositories.base import SQLAlchemyRepository


class FeatureFlagRepository(SQLAlchemyRepository[FeatureFlagModel]):
    model = FeatureFlagModel

    async def get_by_key(self, tenant_id: str, key: str) -> FeatureFlagModel | None:
        stmt = select(FeatureFlagModel).where(FeatureFlagModel.tenant_id == tenant_id, FeatureFlagModel.key == key)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, scope: str | None = None) -> list[FeatureFlagModel]:
        stmt = select(FeatureFlagModel).where(FeatureFlagModel.tenant_id == tenant_id)
        if scope:
            stmt = stmt.where(FeatureFlagModel.scope == scope)
        return list((await self.session.execute(stmt)).scalars().all())


class FeatureFlagOverrideRepository(SQLAlchemyRepository[FeatureFlagOverrideModel]):
    model = FeatureFlagOverrideModel

    async def get_for_target(self, tenant_id: str, flag_id: str, target_ref: str) -> FeatureFlagOverrideModel | None:
        stmt = select(FeatureFlagOverrideModel).where(
            FeatureFlagOverrideModel.tenant_id == tenant_id,
            FeatureFlagOverrideModel.flag_id == flag_id,
            FeatureFlagOverrideModel.target_ref == target_ref,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_flag(self, tenant_id: str, flag_id: str) -> list[FeatureFlagOverrideModel]:
        stmt = select(FeatureFlagOverrideModel).where(
            FeatureFlagOverrideModel.tenant_id == tenant_id, FeatureFlagOverrideModel.flag_id == flag_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())
