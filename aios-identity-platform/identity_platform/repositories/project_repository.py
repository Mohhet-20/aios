from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.project import ProjectModel
from identity_platform.repositories.base import SQLAlchemyRepository


class ProjectRepository(SQLAlchemyRepository[ProjectModel]):
    model = ProjectModel

    async def list_for_workspace(self, workspace_id: str) -> list[ProjectModel]:
        stmt = select(ProjectModel).where(ProjectModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())
