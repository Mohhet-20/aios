import pytest

from identity_platform.domain.enums import UserStatus
from identity_platform.governance.compliance_service import ComplianceService
from identity_platform.mfa.mfa_service import MfaService
from identity_platform.models.user import UserModel
from identity_platform.organizations.membership_service import MembershipService
from identity_platform.organizations.organization_service import OrganizationService
from identity_platform.security.totp import generate_totp

pytestmark = pytest.mark.asyncio


async def _make_org(repos, db_session, name: str, email: str):
    owner = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(owner)
    await db_session.commit()
    org = await OrganizationService(repos).create_organization(name=name, owner_user_id=owner.id)
    await db_session.commit()
    return org, owner


async def test_update_compliance_metadata_merges(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Compliance Co", "compliance-owner@example.com")
    service = ComplianceService(repos)

    await service.update_compliance_metadata(org.id, metadata={"data_residency": "eu"})
    await db_session.commit()
    merged = await service.update_compliance_metadata(org.id, metadata={"frameworks": ["SOC2"]})
    await db_session.commit()

    assert merged == {"data_residency": "eu", "frameworks": ["SOC2"]}


async def test_export_user_data_includes_expected_sections(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Export Co", "export-owner@example.com")
    service = ComplianceService(repos)

    export = await service.export_user_data(owner.id)
    assert export.user_id == owner.id
    assert export.profile["email"] == owner.email
    assert len(export.organization_memberships) == 1
    assert export.organization_memberships[0]["organization_id"] == org.id


async def test_compliance_summary_reflects_mfa_adoption(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Summary Co", "summary-owner@example.com")
    member = UserModel(email="summary-member@example.com", status=UserStatus.ACTIVE.value)
    await repos.users.add(member)
    await db_session.commit()

    membership_service = MembershipService(repos)
    await membership_service.add_organization_member(org.id, member.id)
    await db_session.commit()

    mfa_service = MfaService(repos)
    enrollment = await mfa_service.enroll_totp(owner.id, account_email=owner.email)
    await db_session.commit()
    await mfa_service.confirm_enrollment(enrollment.factor_id, generate_totp(enrollment.raw_secret))
    await db_session.commit()

    service = ComplianceService(repos)
    summary = await service.compliance_summary(org.id)

    assert summary["active_member_count"] == 2
    assert summary["mfa_enabled_member_count"] == 1
    assert summary["mfa_adoption_rate"] == 0.5
