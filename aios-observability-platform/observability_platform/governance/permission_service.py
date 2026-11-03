"""Access control for the observability platform itself: a small
ordered `ObservabilityRole` (viewer < operator < admin), deliberately
simpler than the Identity Platform's fine-grained resource_type:action
grammar (that engine already exists one layer down for platform-wide
RBAC — this one only needs to answer "can this principal view
telemetry / operate on alerts & incidents / administer rules &
retention").

Resolution precedence, most specific wins: a component-scoped grant
overrides a tenant-wide grant (`component_id=None`) for the same
principal. This mirrors the Collaboration Platform's asset-level-
override-beats-workspace-level-grant precedence for the same reason —
"this person can administer everything except the payments service"
needs a narrower override, not a second full grant."""
from __future__ import annotations

from observability_platform.core.exceptions import PermissionDeniedError, ValidationError
from observability_platform.domain.enums import ObservabilityRole, role_at_least
from observability_platform.models.governance import AccessGrantModel
from observability_platform.repositories.registry import RepositoryRegistry


class PermissionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def grant(
        self, tenant_id: str, principal_id: str, role: str, *, component_id: str | None = None
    ) -> AccessGrantModel:
        if role not in {r.value for r in ObservabilityRole}:
            raise ValidationError(f"Unknown observability role '{role}'")
        grant = AccessGrantModel(tenant_id=tenant_id, principal_id=principal_id, role=role, component_id=component_id)
        return await self.repos.access_grants.add(grant)

    async def revoke(self, tenant_id: str, grant_id: str) -> None:
        grant = await self.repos.access_grants.get_or_404(grant_id)
        await self.repos.access_grants.delete(grant)

    async def effective_role(
        self, tenant_id: str, principal_id: str, *, component_id: str | None = None
    ) -> ObservabilityRole | None:
        grants = await self.repos.access_grants.list_for_principal(tenant_id, principal_id)
        if not grants:
            return None

        scoped = [g for g in grants if component_id is not None and g.component_id == component_id]
        candidates = scoped if scoped else [g for g in grants if g.component_id is None]
        if not candidates:
            return None
        best = max(candidates, key=lambda g: ObservabilityRole(g.role).rank)
        return ObservabilityRole(best.role)

    async def require_role(
        self, tenant_id: str, principal_id: str, minimum: ObservabilityRole, *, component_id: str | None = None
    ) -> None:
        role = await self.effective_role(tenant_id, principal_id, component_id=component_id)
        if role is None or not role_at_least(role, minimum):
            raise PermissionDeniedError(
                f"Principal '{principal_id}' lacks at least '{minimum.value}' access"
                + (f" on component '{component_id}'" if component_id else "")
            )
