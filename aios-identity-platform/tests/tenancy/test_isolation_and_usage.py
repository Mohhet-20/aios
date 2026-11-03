import pytest

from identity_platform.core.exceptions import QuotaExceededError, TenantIsolationError
from identity_platform.domain.enums import TenantTier, UserStatus
from identity_platform.models.user import UserModel
from identity_platform.organizations.organization_service import OrganizationService
from identity_platform.organizations.project_service import ProjectService
from identity_platform.organizations.workspace_service import WorkspaceService
from identity_platform.tenancy.isolation import TenantIsolationGuard
from identity_platform.tenancy.tier_service import TenantTierService
from identity_platform.tenancy.usage_service import TenantUsageService

pytestmark = pytest.mark.asyncio


async def _make_org(repos, db_session, name: str, email: str):
    owner = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(owner)
    await db_session.commit()
    org = await OrganizationService(repos).create_organization(name=name, owner_user_id=owner.id)
    await db_session.commit()
    return org, owner


async def test_isolation_guard_allows_matching_organization(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Isolation Co", "isolation-owner@example.com")
    workspace = await WorkspaceService(repos).create_workspace(org.id, name="WS")
    await db_session.commit()

    TenantIsolationGuard.assert_workspace_in_organization(workspace, org.id)


async def test_isolation_guard_rejects_cross_tenant_access(repos, db_session):
    org_a, _ = await _make_org(repos, db_session, "Tenant A", "tenant-a-owner@example.com")
    org_b, _ = await _make_org(repos, db_session, "Tenant B", "tenant-b-owner@example.com")
    workspace_a = await WorkspaceService(repos).create_workspace(org_a.id, name="WS A")
    await db_session.commit()

    with pytest.raises(TenantIsolationError):
        TenantIsolationGuard.assert_workspace_in_organization(workspace_a, org_b.id)


async def test_project_isolation_checks(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Project Isolation Co", "proj-iso-owner@example.com")
    workspace = await WorkspaceService(repos).create_workspace(org.id, name="WS")
    other_workspace = await WorkspaceService(repos).create_workspace(org.id, name="WS Other")
    await db_session.commit()
    project = await ProjectService(repos).create_project(workspace.id, name="Proj")
    await db_session.commit()

    TenantIsolationGuard.assert_project_in_organization(project, org.id)
    with pytest.raises(TenantIsolationError):
        TenantIsolationGuard.assert_project_in_workspace(project, other_workspace.id)


async def test_tenant_usage_reflects_seats_and_workspaces(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Usage Co", "usage-owner@example.com")
    await WorkspaceService(repos).create_workspace(org.id, name="WS 1")
    await db_session.commit()

    usage = await TenantUsageService(repos).get_usage(org.id)
    assert usage.seat_count == 1  # just the owner
    assert usage.workspace_count == 1
    assert usage.seat_quota == org.seat_quota
    assert 0 < usage.seat_utilization <= 1
    assert usage.is_over_seat_quota is False


async def test_tier_upgrade_updates_quotas(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Tier Co", "tier-owner@example.com")
    tier_service = TenantTierService(repos)

    updated = await tier_service.change_tier(org.id, TenantTier.ENTERPRISE)
    await db_session.commit()

    assert updated.tenant_tier == "enterprise"
    assert updated.seat_quota == 10_000
    assert updated.workspace_quota == 1_000


async def test_tier_downgrade_rejected_when_over_new_quota(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Downgrade Co", "downgrade-owner@example.com")
    await WorkspaceService(repos).create_workspace(org.id, name="WS 1")
    await WorkspaceService(repos).create_workspace(org.id, name="WS 2")
    await db_session.commit()

    tier_service = TenantTierService(repos)
    with pytest.raises(QuotaExceededError):
        await tier_service.change_tier(org.id, TenantTier.FREE)  # free tier allows only 1 workspace


async def test_tier_downgrade_with_force_bypasses_check(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Force Downgrade Co", "force-downgrade-owner@example.com")
    await WorkspaceService(repos).create_workspace(org.id, name="WS 1")
    await WorkspaceService(repos).create_workspace(org.id, name="WS 2")
    await db_session.commit()

    tier_service = TenantTierService(repos)
    updated = await tier_service.change_tier(org.id, TenantTier.FREE, force=True)
    await db_session.commit()
    assert updated.tenant_tier == "free"
