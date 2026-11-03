"""FolderService: nested folders within a workspace/project, used to
organize assets. Cycle prevention on `move_folder` matters — a folder
becoming its own ancestor would make tree traversal infinite."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ValidationError
from collaboration_platform.models.workspace import FolderModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class FolderService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_folder(self, workspace_id: str, *, name: str, project_id: str | None = None, parent_folder_id: str | None = None) -> FolderModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        if parent_folder_id is not None:
            await self.repos.folders.get_or_404(parent_folder_id)
        return await self.repos.folders.add(
            FolderModel(workspace_id=workspace_id, project_id=project_id, parent_folder_id=parent_folder_id, name=name)
        )

    async def rename(self, folder_id: str, *, name: str) -> FolderModel:
        folder = await self.repos.folders.get_or_404(folder_id)
        folder.name = name
        return await self.repos.folders.update(folder)

    async def move(self, folder_id: str, *, new_parent_folder_id: str | None) -> FolderModel:
        folder = await self.repos.folders.get_or_404(folder_id)
        if new_parent_folder_id is not None:
            if new_parent_folder_id == folder_id:
                raise ValidationError(f"folder '{folder_id}' cannot be its own parent")
            await self._assert_not_descendant(folder_id, new_parent_folder_id)
        folder.parent_folder_id = new_parent_folder_id
        return await self.repos.folders.update(folder)

    async def _assert_not_descendant(self, folder_id: str, candidate_parent_id: str) -> None:
        """Walks candidate_parent_id's ancestor chain; if folder_id
        appears in it, moving folder_id under candidate_parent_id would
        create a cycle."""
        current_id: str | None = candidate_parent_id
        seen: set[str] = set()
        while current_id is not None:
            if current_id == folder_id:
                raise ValidationError(f"moving folder '{folder_id}' under '{candidate_parent_id}' would create a cycle")
            if current_id in seen:
                break
            seen.add(current_id)
            current = await self.repos.folders.get(current_id)
            current_id = current.parent_folder_id if current else None

    async def list_for_workspace(self, workspace_id: str) -> list[FolderModel]:
        return await self.repos.folders.list_for_workspace(workspace_id)

    async def list_children(self, parent_folder_id: str) -> list[FolderModel]:
        return await self.repos.folders.list_children(parent_folder_id)
