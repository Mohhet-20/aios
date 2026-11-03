from __future__ import annotations

from sqlalchemy import or_, select

from workflow_platform.models.template import WorkflowTemplateModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class WorkflowTemplateRepository(SQLAlchemyRepository[WorkflowTemplateModel]):
    model = WorkflowTemplateModel

    async def list_visible_to_workspace(self, workspace_id: str, *, category: str | None = None) -> list[WorkflowTemplateModel]:
        stmt = select(WorkflowTemplateModel).where(
            or_(WorkflowTemplateModel.workspace_id == workspace_id, WorkflowTemplateModel.is_public.is_(True))
        )
        if category:
            stmt = stmt.where(WorkflowTemplateModel.category == category)
        return list((await self.session.execute(stmt)).scalars().all())
