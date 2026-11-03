from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.autoscaling import ScalingEventModel, ScalingPolicyModel
from infra_platform.repositories.base import SQLAlchemyRepository


class ScalingPolicyRepository(SQLAlchemyRepository[ScalingPolicyModel]):
    model = ScalingPolicyModel

    async def list_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> list[ScalingPolicyModel]:
        stmt = select(ScalingPolicyModel).where(
            ScalingPolicyModel.tenant_id == tenant_id, ScalingPolicyModel.resource_type == resource_type,
            ScalingPolicyModel.resource_id == resource_id, ScalingPolicyModel.is_deleted.is_(False),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_enabled_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> list[ScalingPolicyModel]:
        stmt = select(ScalingPolicyModel).where(
            ScalingPolicyModel.tenant_id == tenant_id, ScalingPolicyModel.resource_type == resource_type,
            ScalingPolicyModel.resource_id == resource_id, ScalingPolicyModel.is_deleted.is_(False), ScalingPolicyModel.is_enabled.is_(True),
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ScalingEventRepository(SQLAlchemyRepository[ScalingEventModel]):
    model = ScalingEventModel

    async def list_for_policy(self, tenant_id: str, policy_id: str, *, limit: int = 200) -> list[ScalingEventModel]:
        stmt = select(ScalingEventModel).where(
            ScalingEventModel.tenant_id == tenant_id, ScalingEventModel.policy_id == policy_id
        ).order_by(ScalingEventModel.occurred_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
