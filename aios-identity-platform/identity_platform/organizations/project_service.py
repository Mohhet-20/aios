"""ProjectService: the finest-grained scope in the org hierarchy;
every project belongs to exactly one workspace."""
from __future__ import annotations

from slugify import slugify

from identity_platform.core.exceptions import ConflictError
from identity_platform.domain.enums import ProjectStatus
from identity_platform.models.project import ProjectModel
from identity_platform.repositories.registry import RepositoryRegistry


class ProjectService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_project(self, workspace_id: str, *, name: str, slug: str | None = None, description: str | None = None) -> ProjectModel:
        workspace = await self.repos.workspaces.get_or_404(workspace_id)

        existing = [p for p in await self.repos.projects.list_for_workspace(workspace_id) if p.slug == slugify(slug or name)]
        if existing:
            raise ConflictError(f"project slug '{existing[0].slug}' already exists in this workspace")

        return await self.repos.projects.add(ProjectModel(
            organization_id=workspace.organization_id, workspace_id=workspace_id, name=name,
            slug=slugify(slug or name), description=description, status=ProjectStatus.ACTIVE.value,
        ))

    async def archive(self, project_id: str) -> ProjectModel:
        project = await self.repos.projects.get_or_404(project_id)
        project.status = ProjectStatus.ARCHIVED.value
        return await self.repos.projects.update(project)

    async def list_for_workspace(self, workspace_id: str) -> list[ProjectModel]:
        return await self.repos.projects.list_for_workspace(workspace_id)
