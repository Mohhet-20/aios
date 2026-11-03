from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.feature_store import FeatureGroupModel, FeatureModel, FeatureValidationRuleModel
from infra_platform.repositories.base import SQLAlchemyRepository


class FeatureGroupRepository(SQLAlchemyRepository[FeatureGroupModel]):
    model = FeatureGroupModel

    async def get_by_name(self, tenant_id: str, name: str) -> FeatureGroupModel | None:
        stmt = select(FeatureGroupModel).where(FeatureGroupModel.tenant_id == tenant_id, FeatureGroupModel.name == name, FeatureGroupModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[FeatureGroupModel]:
        stmt = select(FeatureGroupModel).where(FeatureGroupModel.tenant_id == tenant_id, FeatureGroupModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())


class FeatureRepository(SQLAlchemyRepository[FeatureModel]):
    model = FeatureModel

    async def list_for_group(self, tenant_id: str, feature_group_id: str) -> list[FeatureModel]:
        stmt = select(FeatureModel).where(FeatureModel.tenant_id == tenant_id, FeatureModel.feature_group_id == feature_group_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_name_in_group(self, tenant_id: str, feature_group_id: str, name: str) -> FeatureModel | None:
        stmt = select(FeatureModel).where(
            FeatureModel.tenant_id == tenant_id, FeatureModel.feature_group_id == feature_group_id, FeatureModel.name == name
        ).order_by(FeatureModel.version.desc())
        return (await self.session.execute(stmt)).scalars().first()


class FeatureValidationRuleRepository(SQLAlchemyRepository[FeatureValidationRuleModel]):
    model = FeatureValidationRuleModel

    async def list_for_feature(self, tenant_id: str, feature_id: str) -> list[FeatureValidationRuleModel]:
        stmt = select(FeatureValidationRuleModel).where(
            FeatureValidationRuleModel.tenant_id == tenant_id, FeatureValidationRuleModel.feature_id == feature_id
        )
        return list((await self.session.execute(stmt)).scalars().all())
