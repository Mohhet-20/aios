"""TenantTierService: maps a `TenantTier` to its seat/workspace quota
preset and applies it on upgrade/downgrade. Downgrading is refused if
the organization's current usage already exceeds the target tier's
quota — forcing an operator to reduce usage first rather than silently
leaving the org over quota."""
from __future__ import annotations

from identity_platform.core.exceptions import QuotaExceededError
from identity_platform.domain.enums import TenantTier
from identity_platform.models.organization import OrganizationModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.tenancy.usage_service import TenantUsageService

TIER_QUOTAS: dict[TenantTier, dict[str, int]] = {
    TenantTier.FREE: {"seat_quota": 5, "workspace_quota": 1},
    TenantTier.PRO: {"seat_quota": 50, "workspace_quota": 10},
    TenantTier.ENTERPRISE: {"seat_quota": 10_000, "workspace_quota": 1_000},
}


class TenantTierService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.usage_service = TenantUsageService(repos)

    async def change_tier(self, organization_id: str, new_tier: TenantTier, *, force: bool = False) -> OrganizationModel:
        org = await self.repos.organizations.get_or_404(organization_id)
        preset = TIER_QUOTAS[new_tier]

        if not force:
            usage = await self.usage_service.get_usage(organization_id)
            if usage.seat_count > preset["seat_quota"]:
                raise QuotaExceededError(
                    f"cannot move organization '{organization_id}' to '{new_tier.value}': "
                    f"{usage.seat_count} active seats exceeds the tier's {preset['seat_quota']} seat quota"
                )
            if usage.workspace_count > preset["workspace_quota"]:
                raise QuotaExceededError(
                    f"cannot move organization '{organization_id}' to '{new_tier.value}': "
                    f"{usage.workspace_count} active workspaces exceeds the tier's {preset['workspace_quota']} workspace quota"
                )

        org.tenant_tier = new_tier.value
        org.seat_quota = preset["seat_quota"]
        org.workspace_quota = preset["workspace_quota"]
        return await self.repos.organizations.update(org)
