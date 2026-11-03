"""License Manager: enterprise/organization/trial/feature/seat-based
licenses across the 5 declared types, seat assignment with a usage
cap, an inline-guarded active/suspended/revoked/expired status field
(a "simple status field" resource, no dedicated domain entity), and
offline license validation via `license_rules.verify_offline_license`
for air-gapped installations that can't call back to this service."""
from __future__ import annotations

from datetime import datetime, timedelta

from release_platform.config.settings import get_settings
from release_platform.core.exceptions import (
    InvalidTransitionError,
    LicenseError,
    LicenseExpiredError,
    LicenseNotFoundError,
    SeatLimitExceededError,
)
from release_platform.licensing.license_rules import is_expired
from release_platform.models.license import LicenseModel
from release_platform.repositories.registry import RepositoryRegistry
from release_platform.clock import utc_now

_LICENSE_TRANSITIONS: dict[str, set[str]] = {
    "trial": {"active", "expired", "revoked"},
    "active": {"suspended", "revoked", "expired"},
    "suspended": {"active", "revoked"},
    "expired": set(),
    "revoked": set(),
}


class LicenseService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, license_id: str) -> LicenseModel:
        lic = await self.repos.licenses.get_or_404(license_id)
        if lic.tenant_id != tenant_id:
            raise LicenseNotFoundError(f"License '{license_id}' not found for tenant '{tenant_id}'")
        return lic

    async def issue_license(
        self, tenant_id: str, *, org_ref: str, license_type: str, seats_total: int = 0,
        features: list[str] | None = None, expires_at: datetime | None = None,
    ) -> LicenseModel:
        if license_type not in self.settings.license_types:
            raise LicenseError(f"Unsupported license type '{license_type}'")
        now = utc_now()
        status = "trial" if license_type == "trial" else "active"
        if license_type == "trial" and expires_at is None:
            expires_at = now + timedelta(days=self.settings.default_trial_days)
        lic = LicenseModel(
            tenant_id=tenant_id, org_ref=org_ref, license_type=license_type, status=status,
            seats_total=seats_total, seats_used=0, features=features or [], issued_at=now, expires_at=expires_at,
        )
        return await self.repos.licenses.add(lic)

    async def assign_seat(self, tenant_id: str, license_id: str) -> LicenseModel:
        lic = await self.get_or_404(tenant_id, license_id)
        if lic.seats_total > 0 and lic.seats_used >= lic.seats_total:
            raise SeatLimitExceededError(f"License '{license_id}' has no seats remaining ({lic.seats_used}/{lic.seats_total})")
        lic.seats_used += 1
        return lic

    async def release_seat(self, tenant_id: str, license_id: str) -> LicenseModel:
        lic = await self.get_or_404(tenant_id, license_id)
        lic.seats_used = max(lic.seats_used - 1, 0)
        return lic

    async def _transition(self, tenant_id: str, license_id: str, target: str) -> LicenseModel:
        lic = await self.get_or_404(tenant_id, license_id)
        if target not in _LICENSE_TRANSITIONS.get(lic.status, set()):
            raise InvalidTransitionError(f"Cannot transition license from '{lic.status}' to '{target}'")
        lic.status = target
        return lic

    async def activate(self, tenant_id: str, license_id: str) -> LicenseModel:
        return await self._transition(tenant_id, license_id, "active")

    async def suspend(self, tenant_id: str, license_id: str) -> LicenseModel:
        return await self._transition(tenant_id, license_id, "suspended")

    async def revoke(self, tenant_id: str, license_id: str) -> LicenseModel:
        return await self._transition(tenant_id, license_id, "revoked")

    async def expire(self, tenant_id: str, license_id: str) -> LicenseModel:
        return await self._transition(tenant_id, license_id, "expired")

    async def assert_active(self, tenant_id: str, license_id: str) -> LicenseModel:
        """Subscription validation: raises if the license isn't
        actively usable right now — wrong status, or past its expiry
        date (checked live even if the status field hasn't been swept
        to 'expired' yet by a background job)."""
        lic = await self.get_or_404(tenant_id, license_id)
        if lic.status not in {"active", "trial"}:
            raise LicenseError(f"License '{license_id}' is '{lic.status}', not usable")
        if is_expired(lic.expires_at):
            raise LicenseExpiredError(f"License '{license_id}' expired at {lic.expires_at}")
        return lic

    async def has_feature(self, tenant_id: str, license_id: str, feature: str) -> bool:
        lic = await self.get_or_404(tenant_id, license_id)
        return feature in lic.features

    async def list_for_org(self, tenant_id: str, org_ref: str) -> list[LicenseModel]:
        return await self.repos.licenses.list_for_org(tenant_id, org_ref)
