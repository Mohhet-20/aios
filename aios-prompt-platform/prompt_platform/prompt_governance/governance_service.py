"""Prompt Governance: RBAC + access control (permission grants scoped to
workspace/project/prompt, resolved with prompt > project > workspace >
ownership precedence), the append-only audit trail, sensitive-prompt
protection, and a compliance rollup used to answer "can we trust this
prompt is being managed responsibly."

Approval workflows themselves (version review, deployment approval) are
implemented where the thing being approved lives — versioning_service.py
and deployment_service.py — governance's job here is the cross-cutting
authorization check those (and every other) service can call before
acting, plus the audit record of what happened.
"""
from __future__ import annotations

from prompt_platform.core.exceptions import AuthorizationError
from prompt_platform.domain.enums import Permission, Role, permissions_for_role
from prompt_platform.models.governance import AuditLogEntryModel, PromptPermissionGrantModel
from prompt_platform.models.prompt import PromptModel
from prompt_platform.repositories.registry import RepositoryRegistry

_RESOURCE_PRECEDENCE = ("prompt", "project", "workspace")


class GovernanceService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- RBAC / access control ------------------------------------------------

    async def grant_permission(
        self, resource_type: str, resource_id: str, principal_id: str, role: Role, *,
        granted_by: str, principal_type: str = "user",
    ) -> PromptPermissionGrantModel:
        if resource_type not in _RESOURCE_PRECEDENCE:
            raise ValueError(f"resource_type must be one of {_RESOURCE_PRECEDENCE}")
        grant = await self.repos.permission_grants.add(
            PromptPermissionGrantModel(
                principal_id=principal_id, principal_type=principal_type, resource_type=resource_type,
                resource_id=resource_id, role=role.value, granted_by=granted_by,
            )
        )
        await self.log_action(granted_by, "permission_granted", resource_type, resource_id, after={"principal_id": principal_id, "role": role.value})
        return grant

    async def revoke_permission(self, grant_id: str, *, actor_id: str) -> None:
        grant = await self.repos.permission_grants.get_or_404(grant_id)
        await self.repos.permission_grants.delete(grant, hard=True)
        await self.log_action(actor_id, "permission_revoked", grant.resource_type, grant.resource_id, before={"principal_id": grant.principal_id, "role": grant.role})

    async def _best_grant_role(self, principal_id: str, resource_type: str, resource_id: str) -> Role | None:
        grants = await self.repos.permission_grants.list_for_resource(resource_type, resource_id)
        matching = [g for g in grants if g.principal_id == principal_id]
        if not matching:
            return None
        # If a principal somehow has multiple grants on the same exact
        # resource, the most permissive one wins.
        roles = [Role(g.role) for g in matching]
        return max(roles, key=lambda r: len(permissions_for_role(r)))

    async def effective_role_for_prompt(self, principal_id: str, prompt: PromptModel) -> Role | None:
        """Resolves prompt > project > workspace grant precedence, falling
        back to an implicit OWNER role for the prompt's owner_id."""
        for resource_type, resource_id in (
            ("prompt", prompt.id), ("project", prompt.project_id), ("workspace", prompt.workspace_id),
        ):
            role = await self._best_grant_role(principal_id, resource_type, resource_id)
            if role is not None:
                return role
        if principal_id == prompt.owner_id:
            return Role.OWNER
        return None

    async def check_permission_on_prompt(self, principal_id: str, prompt: PromptModel, permission: Permission) -> bool:
        role = await self.effective_role_for_prompt(principal_id, prompt)
        if role is None:
            return False
        return permission in permissions_for_role(role)

    async def require_permission_on_prompt(self, principal_id: str, prompt: PromptModel, permission: Permission) -> None:
        if not await self.check_permission_on_prompt(principal_id, prompt, permission):
            raise AuthorizationError(f"Principal '{principal_id}' lacks permission '{permission.value}' on prompt '{prompt.id}'")

    async def list_grants_for_principal(self, principal_id: str) -> list[PromptPermissionGrantModel]:
        return await self.repos.permission_grants.list_for_principal(principal_id)

    async def list_grants_for_resource(self, resource_type: str, resource_id: str) -> list[PromptPermissionGrantModel]:
        return await self.repos.permission_grants.list_for_resource(resource_type, resource_id)

    # -- sensitive-prompt protection --------------------------------------------

    async def set_sensitive(self, prompt_id: str, sensitive: bool, *, actor_id: str) -> PromptModel:
        prompt = await self.repos.prompts.get_or_404(prompt_id)
        await self.require_permission_on_prompt(actor_id, prompt, Permission.WORKSPACE_MANAGE if sensitive else Permission.PROMPT_WRITE)
        before = prompt.sensitive
        prompt.sensitive = sensitive
        updated = await self.repos.prompts.update(prompt)
        await self.log_action(actor_id, "sensitive_flag_changed", "prompt", prompt_id, before={"sensitive": before}, after={"sensitive": sensitive})
        return updated

    async def assert_access_to_sensitive_prompt(self, principal_id: str, prompt: PromptModel, *, minimum_role: Role = Role.EDITOR) -> None:
        """Sensitive prompts (compliance-flagged, containing regulated or
        confidential content) require at least `minimum_role` even for
        read access — a bare PROMPT_READ grant via a broad workspace-level
        role is not sufficient once a prompt is marked sensitive."""
        if not prompt.sensitive:
            return
        role = await self.effective_role_for_prompt(principal_id, prompt)
        if role is None or len(permissions_for_role(role)) < len(permissions_for_role(minimum_role)):
            raise AuthorizationError(f"Prompt '{prompt.id}' is marked sensitive; principal '{principal_id}' does not have sufficient access")

    # -- audit log ---------------------------------------------------------------

    async def log_action(
        self, actor_id: str, action: str, resource_type: str, resource_id: str, *,
        before: dict | None = None, after: dict | None = None, ip_address: str | None = None,
    ) -> AuditLogEntryModel:
        return await self.repos.audit_log.add(
            AuditLogEntryModel(actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id, before=before, after=after, ip_address=ip_address)
        )

    async def audit_trail(self, resource_type: str, resource_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log.list_for_resource(resource_type, resource_id, limit=limit)

    # -- compliance rollup ---------------------------------------------------------

    async def compliance_report(self, prompt_id: str) -> dict:
        prompt = await self.repos.prompts.get_or_404(prompt_id)
        grants = await self.repos.permission_grants.list_for_resource("prompt", prompt_id)
        audit_entries = await self.repos.audit_log.list_for_resource("prompt", prompt_id, limit=1000)
        versions = await self.repos.versions.list_for_prompt(prompt_id)
        approved_versions = [v for v in versions if v.status == "approved"]
        return {
            "prompt_id": prompt_id,
            "owner_id": prompt.owner_id,
            "sensitive": prompt.sensitive,
            "visibility": prompt.visibility,
            "explicit_grant_count": len(grants),
            "audit_event_count": len(audit_entries),
            "has_production_version": prompt.production_version_id is not None,
            "approved_version_count": len(approved_versions),
            "total_version_count": len(versions),
        }
