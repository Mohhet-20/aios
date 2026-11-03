from __future__ import annotations

from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.repositories.base import SQLAlchemyRepository


class PromptWorkspaceRepository(SQLAlchemyRepository[PromptWorkspaceModel]):
    model = PromptWorkspaceModel

    async def list_by_organization(self, organization_id: str) -> list[PromptWorkspaceModel]:
        return await self.list(filters={"organization_id": organization_id})


class PromptProjectRepository(SQLAlchemyRepository[PromptProjectModel]):
    model = PromptProjectModel

    async def list_by_workspace(self, workspace_id: str) -> list[PromptProjectModel]:
        return await self.list(filters={"workspace_id": workspace_id})
