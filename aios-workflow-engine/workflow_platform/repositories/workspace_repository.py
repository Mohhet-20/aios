from __future__ import annotations

from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class WorkspaceRepository(SQLAlchemyRepository[WorkspaceModel]):
    model = WorkspaceModel

    async def list_by_organization(self, organization_id: str) -> list[WorkspaceModel]:
        return await self.list(filters={"organization_id": organization_id})
