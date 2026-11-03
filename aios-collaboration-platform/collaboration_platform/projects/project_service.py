"""ProjectService: projects live inside a workspace and are the
mid-level grouping between a workspace and individual assets."""
from __future__ import annotations

from slugify import slugify

from collaboration_platform.domain.enums import ProjectStatus
from collaboration_platform.models.workspace import ProjectModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class ProjectService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_project(self, workspace_id: str, *, name: str, slug: str | None = None, description: str | None = None) -> ProjectModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        return await self.repos.projects.add(
            ProjectModel(workspace_id=workspace_id, name=name, slug=slugify(slug or name), description=description)
        )

    async def update(self, project_id: str, *, name: str | None = None, description: str | None = None) -> ProjectModel:
        project = await self.repos.projects.get_or_404(project_id)
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        return await self.repos.projects.update(project)

    async def archive(self, project_id: str) -> ProjectModel:
        project = await self.repos.projects.get_or_404(project_id)
        project.status = ProjectStatus.ARCHIVED.value
        return await self.repos.projects.update(project)

    async def restore(self, project_id: str) -> ProjectModel:
        project = await self.repos.projects.get_or_404(project_id)
        project.status = ProjectStatus.ACTIVE.value
        return await self.repos.projects.update(project)

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None) -> list[ProjectModel]:
        return await self.repos.projects.list_for_workspace(workspace_id, status=status)
