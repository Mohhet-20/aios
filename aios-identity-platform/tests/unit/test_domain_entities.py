import pytest

from identity_platform.core.exceptions import InvalidTransitionError
from identity_platform.domain.entities import (
    ApiKey,
    Invitation,
    MfaFactor,
    OrganizationMembership,
    Session,
    User,
)
from identity_platform.domain.enums import (
    ApiKeyStatus,
    InvitationStatus,
    MembershipStatus,
    MfaFactorStatus,
    SessionStatus,
    UserStatus,
)


# -- User --------------------------------------------------------------------------

def test_user_verify_email_activates():
    user = User(id="u1", email="a@b.com")
    user.verify_email()
    assert user.status == UserStatus.ACTIVE
    assert user.email_verified_at is not None


def test_user_cannot_verify_email_twice():
    user = User(id="u1", email="a@b.com")
    user.verify_email()
    with pytest.raises(InvalidTransitionError):
        user.verify_email()


def test_user_lockout_threshold_and_lock_unlock():
    user = User(id="u1", email="a@b.com")
    user.verify_email()
    for _ in range(4):
        assert user.record_failed_login(threshold=5) is False
    assert user.record_failed_login(threshold=5) is True

    from datetime import datetime, timezone
    until = datetime.now(timezone.utc)
    user.lock(until=until)
    assert user.status == UserStatus.LOCKED

    user.unlock()
    assert user.status == UserStatus.ACTIVE
    assert user.failed_login_count == 0
    assert user.locked_until is None


def test_user_suspend_and_reinstate():
    user = User(id="u1", email="a@b.com", status=UserStatus.ACTIVE)
    user.suspend()
    assert user.status == UserStatus.SUSPENDED
    user.reinstate()
    assert user.status == UserStatus.ACTIVE


def test_user_deactivate_is_terminal():
    user = User(id="u1", email="a@b.com", status=UserStatus.ACTIVE)
    user.deactivate()
    assert user.status == UserStatus.DEACTIVATED
    with pytest.raises(InvalidTransitionError):
        user.reinstate()


# -- Session -----------------------------------------------------------------------

def test_session_revoke():
    session = Session(id="s1", user_id="u1")
    session.revoke(reason="user logout")
    assert session.status == SessionStatus.REVOKED
    assert session.revoked_reason == "user logout"


def test_session_expire():
    session = Session(id="s1", user_id="u1")
    session.expire()
    assert session.status == SessionStatus.EXPIRED


def test_session_terminal_states_reject_further_transitions():
    session = Session(id="s1", user_id="u1")
    session.revoke(reason="x")
    with pytest.raises(InvalidTransitionError):
        session.expire()


# -- Invitation ------------------------------------------------------------------

def test_invitation_accept():
    invitation = Invitation(id="i1", email="a@b.com")
    invitation.accept(user_id="u1")
    assert invitation.status == InvitationStatus.ACCEPTED
    assert invitation.accepted_by_user_id == "u1"


def test_invitation_revoke_and_expire_are_terminal():
    invitation = Invitation(id="i1", email="a@b.com")
    invitation.revoke()
    assert invitation.status == InvitationStatus.REVOKED
    with pytest.raises(InvalidTransitionError):
        invitation.accept(user_id="u1")


# -- ApiKey --------------------------------------------------------------------------

def test_api_key_revoke_and_expire():
    key = ApiKey(id="k1")
    key.revoke(reason="rotated")
    assert key.status == ApiKeyStatus.REVOKED
    with pytest.raises(InvalidTransitionError):
        key.expire()


# -- OrganizationMembership -----------------------------------------------------------

def test_membership_remove_is_terminal():
    membership = OrganizationMembership(id="m1", organization_id="o1", user_id="u1")
    membership.remove()
    assert membership.status == MembershipStatus.REMOVED
    with pytest.raises(InvalidTransitionError):
        membership.activate()


def test_membership_invited_can_activate():
    membership = OrganizationMembership(id="m1", organization_id="o1", user_id="u1", status=MembershipStatus.INVITED)
    membership.activate()
    assert membership.status == MembershipStatus.ACTIVE


# -- MfaFactor -------------------------------------------------------------------------

def test_mfa_factor_verify_then_disable():
    factor = MfaFactor(id="f1", user_id="u1")
    factor.verify()
    assert factor.status == MfaFactorStatus.ACTIVE
    factor.disable()
    assert factor.status == MfaFactorStatus.DISABLED


def test_mfa_factor_disabled_is_terminal():
    factor = MfaFactor(id="f1", user_id="u1")
    factor.disable()
    with pytest.raises(InvalidTransitionError):
        factor.verify()
