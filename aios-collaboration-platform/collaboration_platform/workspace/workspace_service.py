"""WorkspaceService: create/update/archive/restore workspaces, backed
by the guarded `Workspace` domain entity for the archive/restore
lifecycle (so a caller can never silently "restore" an already-active
workspace or archive an already-archived one — the entity raises
`InvalidTransitionError` instead of the ORM layer just no-op'ing)."""
from __future__ import annotations

from slugify import slugify

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.core.exceptions import ConflictError
from collaboration_platform.domain.entities import Workspace
from collaboration_platform.domain.enums import WorkspaceRole, WorkspaceStatus, WorkspaceType
from collaboration_platform.models.workspace import WorkspaceMemberModel, WorkspaceModel
from collaboration_platform.repositories.registry import RepositoryRegistry


def _workspace_to_domain(model: WorkspaceModel) -> Workspace:
    return Workspace(id=model.id, name=model.name, status=WorkspaceStatus(model.status), archived_at=model.archived_at)


def _apply_workspace_domain(entity: Workspace, model: WorkspaceModel) -> None:
    model.status = entity.status.value
    model.archived_at = entity.archived_at


class WorkspaceService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_workspace(
        self, *, name: str, owner_id: str, workspace_type: WorkspaceType = WorkspaceType.TEAM,
        organization_id: str | None = None, slug: str | None = None, description: str | None = None,
        template_id: str | None = None,
    ) -> WorkspaceModel:
        candidate_slug = slugify(slug or name)
        if await self.repos.workspaces.get_by_slug(candidate_slug) is not None:
            raise ConflictError(f"workspace slug '{candidate_slug}' already exists")

        settings: dict = {}
        if template_id is not None:
            template = await self.repos.workspace_templates.get_or_404(template_id)
            settings = dict(template.config)

        workspace = await self.repos.workspaces.add(WorkspaceModel(
            name=name, slug=candidate_slug, workspace_type=workspace_type.value, owner_id=owner_id,
            organization_id=organization_id, template_id=template_id, description=description, settings=settings,
        ))
        await self.repos.workspace_members.add(
            WorkspaceMemberModel(workspace_id=workspace.id, user_id=owner_id, role=WorkspaceRole.OWNER.value)
        )
        return workspace

    async def update(
        self, workspace_id: str, *, name: str | None = None, description: str | None = None, settings: dict | None = None,
        workspace_metadata: dict | None = None,
    ) -> WorkspaceModel:
        workspace = await self.repos.workspaces.get_or_404(workspace_id)
        if name is not None:
            workspace.name = name
        if description is not None:
            workspace.description = description
        if settings is not None:
            workspace.settings = {**workspace.settings, **settings}
        if workspace_metadata is not None:
            workspace.workspace_metadata = {**workspace.workspace_metadata, **workspace_metadata}
        return await self.repos.workspaces.update(workspace)

    async def archive(self, workspace_id: str) -> WorkspaceModel:
        workspace = await self.repos.workspaces.get_or_404(workspace_id)
        entity = _workspace_to_domain(workspace)
        entity.archive()
        _apply_workspace_domain(entity, workspace)
        return await self.repos.workspaces.update(workspace)

    async def restore(self, workspace_id: str) -> WorkspaceModel:
        workspace = await self.repos.workspaces.get_or_404(workspace_id)
        entity = _workspace_to_domain(workspace)
        entity.restore()
        _apply_workspace_domain(entity, workspace)
        return await self.repos.workspaces.update(workspace)

    async def get(self, workspace_id: str) -> WorkspaceModel:
        return await self.repos.workspaces.get_or_404(workspace_id)

    async def list_for_owner(self, owner_id: str) -> list[WorkspaceModel]:
        return await self.repos.workspaces.list_for_owner(owner_id)

    async def list_for_organization(self, organization_id: str) -> list[WorkspaceModel]:
        return await self.repos.workspaces.list_for_organization(organization_id)
