"""WorkspaceService: workspaces live inside an organization and are
capped by `OrganizationModel.workspace_quota` — the quota is enforced
here rather than at the database layer since "how many active
workspaces does this org have" is a business rule, not a constraint."""
from __future__ import annotations

from slugify import slugify

from identity_platform.core.exceptions import ConflictError, QuotaExceededError
from identity_platform.domain.enums import WorkspaceStatus
from identity_platform.models.workspace import WorkspaceModel
from identity_platform.repositories.registry import RepositoryRegistry


class WorkspaceService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_workspace(self, org_id: str, *, name: str, slug: str | None = None, description: str | None = None) -> WorkspaceModel:
        org = await self.repos.organizations.get_or_404(org_id)
        existing = await self.repos.workspaces.list_for_organization(org_id)
        if len(existing) >= org.workspace_quota:
            raise QuotaExceededError(f"organization '{org_id}' has reached its workspace quota ({org.workspace_quota})")

        candidate_slug = slugify(slug or name)
        if await self.repos.workspaces.get_by_slug(org_id, candidate_slug) is not None:
            raise ConflictError(f"workspace slug '{candidate_slug}' already exists in this organization")

        return await self.repos.workspaces.add(WorkspaceModel(
            organization_id=org_id, name=name, slug=candidate_slug, description=description,
            status=WorkspaceStatus.ACTIVE.value,
        ))

    async def update(self, workspace_id: str, *, name: str | None = None, description: str | None = None, settings: dict | None = None) -> WorkspaceModel:
        workspace = await self.repos.workspaces.get_or_404(workspace_id)
        if name is not None:
            workspace.name = name
        if description is not None:
            workspace.description = description
        if settings is not None:
            workspace.settings = {**workspace.settings, **settings}
        return await self.repos.workspaces.update(workspace)

    async def archive(self, workspace_id: str) -> WorkspaceModel:
        workspace = await self.repos.workspaces.get_or_404(workspace_id)
        workspace.status = WorkspaceStatus.ARCHIVED.value
        return await self.repos.workspaces.update(workspace)

    async def list_for_organization(self, org_id: str) -> list[WorkspaceModel]:
        return await self.repos.workspaces.list_for_organization(org_id)
