from __future__ import annotations

from sqlalchemy import func, select

from workflow_platform.models.workflow import WorkflowModel, WorkflowVersionModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class WorkflowRepository(SQLAlchemyRepository[WorkflowModel]):
    model = WorkflowModel

    async def list_by_workspace(self, workspace_id: str, *, status: str | None = None, category: str | None = None) -> list[WorkflowModel]:
        filters = {"workspace_id": workspace_id}
        if status:
            filters["status"] = status
        if category:
            filters["category"] = category
        return await self.list(filters=filters)

    async def get_by_slug(self, workspace_id: str, slug: str) -> WorkflowModel | None:
        stmt = select(WorkflowModel).where(WorkflowModel.workspace_id == workspace_id, WorkflowModel.slug == slug)
        return (await self.session.execute(stmt)).scalars().first()

    async def search(self, workspace_id: str, query: str, *, limit: int = 50) -> list[WorkflowModel]:
        pattern = f"%{query.lower()}%"
        stmt = select(WorkflowModel).where(
            WorkflowModel.workspace_id == workspace_id,
            func.lower(WorkflowModel.name).like(pattern),
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class WorkflowVersionRepository(SQLAlchemyRepository[WorkflowVersionModel]):
    model = WorkflowVersionModel

    async def list_for_workflow(self, workflow_id: str) -> list[WorkflowVersionModel]:
        stmt = select(WorkflowVersionModel).where(WorkflowVersionModel.workflow_id == workflow_id).order_by(WorkflowVersionModel.version_number)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest_version_number(self, workflow_id: str) -> int:
        stmt = select(func.max(WorkflowVersionModel.version_number)).where(WorkflowVersionModel.workflow_id == workflow_id)
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        return result or 0

    async def get_draft_version(self, workflow_id: str) -> WorkflowVersionModel | None:
        stmt = select(WorkflowVersionModel).where(
            WorkflowVersionModel.workflow_id == workflow_id, WorkflowVersionModel.status == "draft"
        ).order_by(WorkflowVersionModel.version_number.desc())
        return (await self.session.execute(stmt)).scalars().first()
