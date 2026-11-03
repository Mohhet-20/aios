from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.validation import ApiValidationRunModel, WorkflowValidationRunModel
from quality_platform.repositories.base import SQLAlchemyRepository


class ApiValidationRunRepository(SQLAlchemyRepository[ApiValidationRunModel]):
    model = ApiValidationRunModel

    async def list_for_tenant(self, tenant_id: str, *, validation_type: str | None = None, limit: int = 100) -> list[ApiValidationRunModel]:
        stmt = select(ApiValidationRunModel).where(ApiValidationRunModel.tenant_id == tenant_id)
        if validation_type:
            stmt = stmt.where(ApiValidationRunModel.validation_type == validation_type)
        stmt = stmt.order_by(ApiValidationRunModel.executed_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class WorkflowValidationRunRepository(SQLAlchemyRepository[WorkflowValidationRunModel]):
    model = WorkflowValidationRunModel

    async def list_for_tenant(self, tenant_id: str, *, workflow_ref: str | None = None, limit: int = 100) -> list[WorkflowValidationRunModel]:
        stmt = select(WorkflowValidationRunModel).where(WorkflowValidationRunModel.tenant_id == tenant_id)
        if workflow_ref:
            stmt = stmt.where(WorkflowValidationRunModel.workflow_ref == workflow_ref)
        stmt = stmt.order_by(WorkflowValidationRunModel.requested_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
