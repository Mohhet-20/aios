import pytest

from identity_platform.authorization.bootstrap import seed_builtin_roles
from identity_platform.core.exceptions import ConflictError, TokenAlreadyUsedError, TokenExpiredError
from identity_platform.domain.enums import PrincipalType, UserStatus
from identity_platform.models.user import UserModel
from identity_platform.organizations.invitation_service import InvitationService
from identity_platform.organizations.membership_service import MembershipService
from identity_platform.organizations.organization_service import OrganizationService

pytestmark = pytest.mark.asyncio


async def _make_user(repos, db_session, email: str) -> UserModel:
    user = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(user)
    await db_session.commit()
    return user


async def _make_org(repos, db_session, name: str, owner_email: str):
    owner = await _make_user(repos, db_session, owner_email)
    org = await OrganizationService(repos).create_organization(name=name, owner_user_id=owner.id)
    await db_session.commit()
    return org, owner


async def test_invitation_accept_creates_membership_and_role(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org, owner = await _make_org(repos, db_session, "Invite Co", "invite-owner@example.com")
    invitee = await _make_user(repos, db_session, "invitee@example.com")
    admin_role = await repos.roles.get_by_slug(None, "org_admin")

    invitation_service = InvitationService(repos)
    invitation, raw_token = await invitation_service.create_invitation(
        org.id, email=invitee.email, invited_by=owner.id, role_id=admin_role.id,
    )
    await db_session.commit()
    assert invitation.status == "pending"

    accepted = await invitation_service.accept_invitation(raw_token, user=invitee)
    await db_session.commit()
    assert accepted.status == "accepted"
    assert accepted.accepted_by_user_id == invitee.id

    membership_service = MembershipService(repos)
    members = await membership_service.list_organization_members(org.id)
    assert any(m.user_id == invitee.id for m in members)

    assignments = await repos.role_assignments.list_for_principal(PrincipalType.USER.value, invitee.id)
    assert any(a.role_id == admin_role.id for a in assignments)


async def test_invitation_cannot_be_accepted_twice(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Invite Twice Co", "invite-twice-owner@example.com")
    invitee = await _make_user(repos, db_session, "invitee-twice@example.com")

    invitation_service = InvitationService(repos)
    _, raw_token = await invitation_service.create_invitation(org.id, email=invitee.email, invited_by=owner.id)
    await db_session.commit()

    await invitation_service.accept_invitation(raw_token, user=invitee)
    await db_session.commit()

    with pytest.raises(TokenAlreadyUsedError):
        await invitation_service.accept_invitation(raw_token, user=invitee)


async def test_duplicate_pending_invitation_rejected(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Invite Dupe Co", "invite-dupe-owner@example.com")
    invitation_service = InvitationService(repos)
    await invitation_service.create_invitation(org.id, email="dupe-invitee@example.com", invited_by=owner.id)
    await db_session.commit()

    with pytest.raises(ConflictError):
        await invitation_service.create_invitation(org.id, email="dupe-invitee@example.com", invited_by=owner.id)


async def test_revoked_invitation_cannot_be_accepted(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Invite Revoke Co", "invite-revoke-owner@example.com")
    invitee = await _make_user(repos, db_session, "invitee-revoke@example.com")

    invitation_service = InvitationService(repos)
    invitation, raw_token = await invitation_service.create_invitation(org.id, email=invitee.email, invited_by=owner.id)
    await db_session.commit()

    await invitation_service.revoke_invitation(invitation.id)
    await db_session.commit()

    with pytest.raises(TokenExpiredError):
        await invitation_service.accept_invitation(raw_token, user=invitee)


async def test_list_pending_invitations(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Invite List Co", "invite-list-owner@example.com")
    invitation_service = InvitationService(repos)
    await invitation_service.create_invitation(org.id, email="pending1@example.com", invited_by=owner.id)
    await invitation_service.create_invitation(org.id, email="pending2@example.com", invited_by=owner.id)
    await db_session.commit()

    pending = await invitation_service.list_pending_for_organization(org.id)
    assert len(pending) == 2
