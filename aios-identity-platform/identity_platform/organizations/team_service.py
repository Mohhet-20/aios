"""TeamService: a team is either org-wide (`workspace_id=None`) or
scoped to one workspace."""
from __future__ import annotations

from slugify import slugify

from identity_platform.core.exceptions import ConflictError
from identity_platform.domain.enums import TeamStatus
from identity_platform.models.team import TeamModel
from identity_platform.repositories.registry import RepositoryRegistry


class TeamService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_team(self, org_id: str, *, name: str, slug: str | None = None, workspace_id: str | None = None, description: str | None = None) -> TeamModel:
        await self.repos.organizations.get_or_404(org_id)
        if workspace_id is not None:
            await self.repos.workspaces.get_or_404(workspace_id)

        existing = [t for t in await self.repos.teams.list_for_organization(org_id) if t.slug == slugify(slug or name)]
        if existing:
            raise ConflictError(f"team slug '{existing[0].slug}' already exists in this organization")

        return await self.repos.teams.add(TeamModel(
            organization_id=org_id, workspace_id=workspace_id, name=name, slug=slugify(slug or name),
            description=description, status=TeamStatus.ACTIVE.value,
        ))

    async def archive(self, team_id: str) -> TeamModel:
        team = await self.repos.teams.get_or_404(team_id)
        team.status = TeamStatus.ARCHIVED.value
        return await self.repos.teams.update(team)

    async def list_for_organization(self, org_id: str) -> list[TeamModel]:
        return await self.repos.teams.list_for_organization(org_id)
