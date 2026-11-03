"""RBAC: workspace/agent-scoped role grants with agent-beats-workspace
precedence (specific beats general — same pattern the Prompt Platform
used for prompt > project > workspace), plus an implicit OWNER role for
an agent's own `owner_id`, mirroring that platform's implicit-owner rule
for a prompt's `owner_id`.
"""
from __future__ import annotations

from agent_platform.domain.enums import Permission, Role, permissions_for_role
from agent_platform.models.agent import AgentModel
from agent_platform.models.governance import PermissionGrantModel
from agent_platform.repositories.registry import RepositoryRegistry


class RBACService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def grant(self, principal_id: str, resource_type: str, resource_id: str, role: Role, *, granted_by: str, principal_type: str = "user") -> PermissionGrantModel:
        return await self.repos.permission_grants.add(PermissionGrantModel(
            principal_id=principal_id, principal_type=principal_type, resource_type=resource_type,
            resource_id=resource_id, role=role.value, granted_by=granted_by,
        ))

    async def revoke(self, grant_id: str) -> None:
        grant = await self.repos.permission_grants.get_or_404(grant_id)
        await self.repos.permission_grants.delete(grant, hard=True)

    async def list_for_principal(self, principal_id: str) -> list[PermissionGrantModel]:
        return await self.repos.permission_grants.list_for_principal(principal_id)

    async def _direct_role(self, principal_id: str, resource_type: str, resource_id: str) -> Role | None:
        grants = await self.repos.permission_grants.list_for_resource(resource_type, resource_id)
        for grant in grants:
            if grant.principal_id == principal_id:
                return Role(grant.role)
        return None

    async def effective_role_for_agent(self, principal_id: str, agent: AgentModel) -> Role | None:
        if agent.owner_id == principal_id:
            return Role.OWNER
        agent_role = await self._direct_role(principal_id, "agent", agent.id)
        if agent_role is not None:
            return agent_role
        return await self._direct_role(principal_id, "workspace", agent.workspace_id)

    async def effective_role_for_workspace(self, principal_id: str, workspace_id: str) -> Role | None:
        return await self._direct_role(principal_id, "workspace", workspace_id)

    async def has_permission(self, principal_id: str, permission: Permission, *, agent: AgentModel | None = None, workspace_id: str | None = None) -> bool:
        if agent is not None:
            role = await self.effective_role_for_agent(principal_id, agent)
        elif workspace_id is not None:
            role = await self.effective_role_for_workspace(principal_id, workspace_id)
        else:
            role = None
        if role is None:
            return False
        return permission in permissions_for_role(role)
