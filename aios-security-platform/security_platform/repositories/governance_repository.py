from __future__ import annotations

from sqlalchemy import select

from security_platform.models.governance import (
    ApprovalDecisionModel,
    ApprovalPolicyModel,
    ApprovalRequestModel,
    GovernanceAssetModel,
)
from security_platform.repositories.base import SQLAlchemyRepository


class GovernanceAssetRepository(SQLAlchemyRepository[GovernanceAssetModel]):
    model = GovernanceAssetModel

    async def get_by_external_ref(self, tenant_id: str, asset_type: str, external_ref_id: str) -> GovernanceAssetModel | None:
        stmt = select(GovernanceAssetModel).where(
            GovernanceAssetModel.tenant_id == tenant_id,
            GovernanceAssetModel.asset_type == asset_type,
            GovernanceAssetModel.external_ref_id == external_ref_id,
            GovernanceAssetModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_lifecycle_stage(self, tenant_id: str, stage: str) -> list[GovernanceAssetModel]:
        stmt = select(GovernanceAssetModel).where(
            GovernanceAssetModel.tenant_id == tenant_id,
            GovernanceAssetModel.is_deleted.is_(False),
            GovernanceAssetModel.lifecycle_stage == stage,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_stage(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = (
            select(GovernanceAssetModel.lifecycle_stage, func.count())
            .where(GovernanceAssetModel.tenant_id == tenant_id, GovernanceAssetModel.is_deleted.is_(False))
            .group_by(GovernanceAssetModel.lifecycle_stage)
        )
        rows = (await self.session.execute(stmt)).all()
        return {stage: count for stage, count in rows}


class ApprovalPolicyRepository(SQLAlchemyRepository[ApprovalPolicyModel]):
    model = ApprovalPolicyModel

    async def get_for_asset_type(self, tenant_id: str, asset_type: str) -> ApprovalPolicyModel | None:
        stmt = select(ApprovalPolicyModel).where(
            ApprovalPolicyModel.tenant_id == tenant_id,
            ApprovalPolicyModel.asset_type == asset_type,
            ApprovalPolicyModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()


class ApprovalRequestRepository(SQLAlchemyRepository[ApprovalRequestModel]):
    model = ApprovalRequestModel

    async def list_pending_for_asset(self, tenant_id: str, asset_id: str) -> list[ApprovalRequestModel]:
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.tenant_id == tenant_id,
            ApprovalRequestModel.asset_id == asset_id,
            ApprovalRequestModel.status.in_(["pending", "in_review"]),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_pending(self, tenant_id: str) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(ApprovalRequestModel).where(
            ApprovalRequestModel.tenant_id == tenant_id, ApprovalRequestModel.status.in_(["pending", "in_review"])
        )
        return (await self.session.execute(stmt)).scalar_one()


class ApprovalDecisionRepository(SQLAlchemyRepository[ApprovalDecisionModel]):
    model = ApprovalDecisionModel

    async def list_for_request(self, tenant_id: str, request_id: str) -> list[ApprovalDecisionModel]:
        stmt = select(ApprovalDecisionModel).where(
            ApprovalDecisionModel.tenant_id == tenant_id, ApprovalDecisionModel.request_id == request_id
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_approvals(self, tenant_id: str, request_id: str) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(ApprovalDecisionModel).where(
            ApprovalDecisionModel.tenant_id == tenant_id,
            ApprovalDecisionModel.request_id == request_id,
            ApprovalDecisionModel.decision == "approve",
        )
        return (await self.session.execute(stmt)).scalar_one()
