import pytest

from release_platform.core.exceptions import (
    InvalidTransitionError,
    LicenseError,
    LicenseExpiredError,
    NotFoundError,
    SeatLimitExceededError,
)
from release_platform.licensing.license_service import LicenseService

pytestmark = pytest.mark.asyncio

TENANT = "t-licensing"


async def test_issue_license_rejects_unsupported_type(repos):
    svc = LicenseService(repos)
    with pytest.raises(LicenseError):
        await svc.issue_license(TENANT, org_ref="org:acme", license_type="lifetime_free")


async def test_get_or_404_raises_for_missing(repos):
    svc = LicenseService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_trial_license_defaults_expiry(repos):
    svc = LicenseService(repos)
    lic = await svc.issue_license(TENANT, org_ref="org:acme", license_type="trial")
    assert lic.status == "trial"
    assert lic.expires_at is not None


async def test_enterprise_license_defaults_active_no_expiry(repos):
    svc = LicenseService(repos)
    lic = await svc.issue_license(TENANT, org_ref="org:acme", license_type="enterprise", seats_total=10)
    assert lic.status == "active"
    assert lic.expires_at is None


async def test_seat_assignment_and_limit(repos):
    svc = LicenseService(repos)
    lic = await svc.issue_license(TENANT, org_ref="org:acme", license_type="seat_based", seats_total=2)
    lic = await svc.assign_seat(TENANT, lic.id)
    lic = await svc.assign_seat(TENANT, lic.id)
    assert lic.seats_used == 2
    with pytest.raises(SeatLimitExceededError):
        await svc.assign_seat(TENANT, lic.id)


async def test_release_seat_floors_at_zero(repos):
    svc = LicenseService(repos)
    lic = await svc.issue_license(TENANT, org_ref="org:acme", license_type="seat_based", seats_total=5)
    lic = await svc.release_seat(TENANT, lic.id)
    assert lic.seats_used == 0


async def test_unlimited_seats_when_total_is_zero(repos):
    svc = LicenseService(repos)
    lic = await svc.issue_license(TENANT, org_ref="org:acme", license_type="enterprise", seats_total=0)
    for _ in range(20):
        lic = await svc.assign_seat(TENANT, lic.id)
    assert lic.seats_used == 20


async def test_status_lifecycle(repos):
    svc = LicenseService(repos)
    lic = await svc.issue_license(TENANT, org_ref="org:acme", license_type="enterprise")
    lic = await svc.suspend(TENANT, lic.id)
    assert lic.status == "suspended"
    lic = await svc.activate(TENANT, lic.id)
    assert lic.status == "active"
    lic = await svc.revoke(TENANT, lic.id)
    assert lic.status == "revoked"


async def test_revoked_is_terminal(repos):
    svc = LicenseService(repos)
    lic = await svc.issue_license(TENANT, org_ref="org:acme", license_type="enterprise")
    lic = await svc.revoke(TENANT, lic.id)
    with pytest.raises(InvalidTransitionError):
        await svc.activate(TENANT, lic.id)


async def test_assert_active_rejects_suspended(repos):
    svc = LicenseService(repos)
    lic = await svc.issue_license(TENANT, org_ref="org:acme", license_type="enterprise")
    await svc.suspend(TENANT, lic.id)
    with pytest.raises(LicenseError):
        await svc.assert_active(TENANT, lic.id)


async def test_assert_active_rejects_expired_trial(repos):
    from datetime import datetime, timedelta, timezone
    svc = LicenseService(repos)
    lic = await svc.issue_license(
        TENANT, org_ref="org:acme", license_type="trial", expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    with pytest.raises(LicenseExpiredError):
        await svc.assert_active(TENANT, lic.id)


async def test_has_feature(repos):
    svc = LicenseService(repos)
    lic = await svc.issue_license(TENANT, org_ref="org:acme", license_type="feature", features=["sso", "audit_logs"])
    assert await svc.has_feature(TENANT, lic.id, "sso") is True
    assert await svc.has_feature(TENANT, lic.id, "custom_domains") is False


async def test_list_for_org(repos):
    svc = LicenseService(repos)
    await svc.issue_license(TENANT, org_ref="org:beta-co", license_type="enterprise")
    await svc.issue_license(TENANT, org_ref="org:beta-co", license_type="trial")
    licenses = await svc.list_for_org(TENANT, "org:beta-co")
    assert len(licenses) == 2
