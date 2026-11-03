"""TenantUsageService: computes quota usage on demand from live counts
rather than maintaining a separately-updated usage-metrics table — for
a resource as cheap to `COUNT()` as "active org members" or "active
workspaces," a cached counter is a consistency bug waiting to happen
(it can drift from reality if any write path forgets to update it),
so this platform intentionally doesn't persist one."""
from __future__ import annotations

from dataclasses import dataclass

from identity_platform.domain.enums import MembershipStatus, WorkspaceStatus
from identity_platform.repositories.registry import RepositoryRegistry


@dataclass
class TenantUsage:
    organization_id: str
    seat_count: int
    seat_quota: int
    workspace_count: int
    workspace_quota: int

    @property
    def seat_utilization(self) -> float:
        return round(self.seat_count / self.seat_quota, 4) if self.seat_quota else 0.0

    @property
    def workspace_utilization(self) -> float:
        return round(self.workspace_count / self.workspace_quota, 4) if self.workspace_quota else 0.0

    @property
    def is_over_seat_quota(self) -> bool:
        return self.seat_count > self.seat_quota

    @property
    def is_over_workspace_quota(self) -> bool:
        return self.workspace_count > self.workspace_quota


class TenantUsageService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_usage(self, organization_id: str) -> TenantUsage:
        org = await self.repos.organizations.get_or_404(organization_id)

        members = await self.repos.organization_memberships.list_for_organization(organization_id)
        seat_count = sum(1 for m in members if m.status == MembershipStatus.ACTIVE.value)

        workspaces = await self.repos.workspaces.list_for_organization(organization_id)
        workspace_count = sum(1 for w in workspaces if w.status == WorkspaceStatus.ACTIVE.value)

        return TenantUsage(
            organization_id=organization_id, seat_count=seat_count, seat_quota=org.seat_quota,
            workspace_count=workspace_count, workspace_quota=org.workspace_quota,
        )
