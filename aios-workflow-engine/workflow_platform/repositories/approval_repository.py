from __future__ import annotations

from sqlalchemy import select

from workflow_platform.models.approval import ApprovalCommentModel, ApprovalRequestModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class ApprovalRequestRepository(SQLAlchemyRepository[ApprovalRequestModel]):
    model = ApprovalRequestModel

    async def list_for_execution(self, execution_id: str) -> list[ApprovalRequestModel]:
        stmt = select(ApprovalRequestModel).where(ApprovalRequestModel.execution_id == execution_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_pending_for_workspace(self, workspace_id: str) -> list[ApprovalRequestModel]:
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.workspace_id == workspace_id,
            ApprovalRequestModel.status == "pending",
        ).order_by(ApprovalRequestModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_escalation_candidates(self, *, as_of) -> list[ApprovalRequestModel]:
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.status == "pending",
            ApprovalRequestModel.escalate_after.is_not(None),
            ApprovalRequestModel.escalate_after <= as_of,
            ApprovalRequestModel.escalated_at.is_(None),
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ApprovalCommentRepository(SQLAlchemyRepository[ApprovalCommentModel]):
    model = ApprovalCommentModel

    async def list_for_approval(self, approval_request_id: str) -> list[ApprovalCommentModel]:
        stmt = (
            select(ApprovalCommentModel)
            .where(ApprovalCommentModel.approval_request_id == approval_request_id)
            .order_by(ApprovalCommentModel.created_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())
