from __future__ import annotations

from sqlalchemy import select

from collaboration_platform.models.review import ApprovalPolicyModel, ReviewAssignmentModel, ReviewRequestModel
from collaboration_platform.repositories.base import SQLAlchemyRepository


class ApprovalPolicyRepository(SQLAlchemyRepository[ApprovalPolicyModel]):
    model = ApprovalPolicyModel

    async def list_for_workspace(self, workspace_id: str) -> list[ApprovalPolicyModel]:
        stmt = select(ApprovalPolicyModel).where(ApprovalPolicyModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_workspace_and_asset_type(self, workspace_id: str, asset_type: str | None) -> ApprovalPolicyModel | None:
        stmt = select(ApprovalPolicyModel).where(
            ApprovalPolicyModel.workspace_id == workspace_id, ApprovalPolicyModel.asset_type == asset_type
        )
        return (await self.session.execute(stmt)).scalars().first()


class ReviewRequestRepository(SQLAlchemyRepository[ReviewRequestModel]):
    model = ReviewRequestModel

    async def list_for_asset(self, asset_id: str) -> list[ReviewRequestModel]:
        stmt = select(ReviewRequestModel).where(ReviewRequestModel.asset_id == asset_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_pending(self) -> list[ReviewRequestModel]:
        stmt = select(ReviewRequestModel).where(ReviewRequestModel.status.in_(["pending", "in_review"]))
        return list((await self.session.execute(stmt)).scalars().all())


class ReviewAssignmentRepository(SQLAlchemyRepository[ReviewAssignmentModel]):
    model = ReviewAssignmentModel

    async def list_for_request(self, review_request_id: str) -> list[ReviewAssignmentModel]:
        stmt = (
            select(ReviewAssignmentModel)
            .where(ReviewAssignmentModel.review_request_id == review_request_id)
            .order_by(ReviewAssignmentModel.sequence_order)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_reviewer(self, reviewer_id: str, *, pending_only: bool = False) -> list[ReviewAssignmentModel]:
        stmt = select(ReviewAssignmentModel).where(ReviewAssignmentModel.reviewer_id == reviewer_id)
        if pending_only:
            stmt = stmt.where(ReviewAssignmentModel.status == "pending")
        return list((await self.session.execute(stmt)).scalars().all())
