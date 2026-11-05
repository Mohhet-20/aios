"""Pure-Python domain aggregates — no ORM/SQLAlchemy imports here, the
same separation every other AIOS platform uses. Each entity owns a
guarded `_transition()` over its own status enum; unlike the
Evaluation Platform's `EvaluationRun`/`BenchmarkRun` (which shared one
`_RunMixin` because their state machines were identical in shape and
non-trivial), the lifecycles here are small enough and different
enough in trigger/side-effect that giving each its own explicit
transition map is clearer than forcing a shared abstraction."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from identity_platform.core.exceptions import InvalidTransitionError
from identity_platform.domain.enums import (
    ApiKeyStatus,
    InvitationStatus,
    MembershipStatus,
    MfaFactorStatus,
    SessionStatus,
    UserStatus,
)
from identity_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on DateTime round-trip; every timestamp this
    platform writes is UTC (`database.base.utcnow`), so a naive value
    reloaded from the database is safely treated as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# -- User --------------------------------------------------------------------------

_USER_TRANSITIONS: dict[UserStatus, set[UserStatus]] = {
    UserStatus.PENDING_VERIFICATION: {UserStatus.ACTIVE, UserStatus.DEACTIVATED},
    UserStatus.ACTIVE: {UserStatus.LOCKED, UserStatus.SUSPENDED, UserStatus.DEACTIVATED},
    UserStatus.LOCKED: {UserStatus.ACTIVE, UserStatus.DEACTIVATED},
    UserStatus.SUSPENDED: {UserStatus.ACTIVE, UserStatus.DEACTIVATED},
    UserStatus.DEACTIVATED: set(),
}


@dataclass
class User:
    id: str
    email: str
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    failed_login_count: int = 0
    locked_until: datetime | None = None
    email_verified_at: datetime | None = None

    def _transition(self, target: UserStatus) -> None:
        allowed = _USER_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"User '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def verify_email(self) -> None:
        self._transition(UserStatus.ACTIVE)
        self.email_verified_at = _now()

    def record_failed_login(self, *, threshold: int) -> bool:
        """Increments the failed-attempt counter and returns True if
        this attempt crossed the lockout threshold (the caller is
        responsible for actually calling `lock()`, since locking also
        needs a lockout-duration policy value)."""
        self.failed_login_count += 1
        return self.failed_login_count >= threshold

    def reset_failed_logins(self) -> None:
        self.failed_login_count = 0

    def lock(self, *, until: datetime) -> None:
        self._transition(UserStatus.LOCKED)
        self.locked_until = until

    def unlock(self) -> None:
        self._transition(UserStatus.ACTIVE)
        self.locked_until = None
        self.failed_login_count = 0

    def suspend(self) -> None:
        self._transition(UserStatus.SUSPENDED)

    def reinstate(self) -> None:
        self._transition(UserStatus.ACTIVE)

    def deactivate(self) -> None:
        self._transition(UserStatus.DEACTIVATED)


# -- Session -----------------------------------------------------------------------

_SESSION_TRANSITIONS: dict[SessionStatus, set[SessionStatus]] = {
    SessionStatus.ACTIVE: {SessionStatus.REVOKED, SessionStatus.EXPIRED},
    SessionStatus.REVOKED: set(),
    SessionStatus.EXPIRED: set(),
}


@dataclass
class Session:
    id: str
    user_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    revoked_reason: str | None = None
    revoked_at: datetime | None = None

    def _transition(self, target: SessionStatus) -> None:
        allowed = _SESSION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Session '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def revoke(self, *, reason: str) -> None:
        self._transition(SessionStatus.REVOKED)
        self.revoked_reason = reason
        self.revoked_at = _now()

    def expire(self) -> None:
        self._transition(SessionStatus.EXPIRED)


# -- Invitation ------------------------------------------------------------------

_INVITATION_TRANSITIONS: dict[InvitationStatus, set[InvitationStatus]] = {
    InvitationStatus.PENDING: {InvitationStatus.ACCEPTED, InvitationStatus.EXPIRED, InvitationStatus.REVOKED},
    InvitationStatus.ACCEPTED: set(),
    InvitationStatus.EXPIRED: set(),
    InvitationStatus.REVOKED: set(),
}


@dataclass
class Invitation:
    id: str
    email: str
    status: InvitationStatus = InvitationStatus.PENDING
    accepted_at: datetime | None = None
    accepted_by_user_id: str | None = None
    revoked_at: datetime | None = None

    def _transition(self, target: InvitationStatus) -> None:
        allowed = _INVITATION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Invitation '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def accept(self, *, user_id: str) -> None:
        self._transition(InvitationStatus.ACCEPTED)
        self.accepted_at = _now()
        self.accepted_by_user_id = user_id

    def expire(self) -> None:
        self._transition(InvitationStatus.EXPIRED)

    def revoke(self) -> None:
        self._transition(InvitationStatus.REVOKED)
        self.revoked_at = _now()


# -- ApiKey --------------------------------------------------------------------------

_API_KEY_TRANSITIONS: dict[ApiKeyStatus, set[ApiKeyStatus]] = {
    ApiKeyStatus.ACTIVE: {ApiKeyStatus.REVOKED, ApiKeyStatus.EXPIRED},
    ApiKeyStatus.REVOKED: set(),
    ApiKeyStatus.EXPIRED: set(),
}


@dataclass
class ApiKey:
    id: str
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE
    revoked_reason: str | None = None
    revoked_at: datetime | None = None

    def _transition(self, target: ApiKeyStatus) -> None:
        allowed = _API_KEY_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ApiKey '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def revoke(self, *, reason: str) -> None:
        self._transition(ApiKeyStatus.REVOKED)
        self.revoked_reason = reason
        self.revoked_at = _now()

    def expire(self) -> None:
        self._transition(ApiKeyStatus.EXPIRED)


# -- OrganizationMembership -----------------------------------------------------------

_MEMBERSHIP_TRANSITIONS: dict[MembershipStatus, set[MembershipStatus]] = {
    MembershipStatus.INVITED: {MembershipStatus.ACTIVE, MembershipStatus.REMOVED},
    MembershipStatus.ACTIVE: {MembershipStatus.REMOVED},
    MembershipStatus.REMOVED: set(),
}


@dataclass
class OrganizationMembership:
    id: str
    organization_id: str
    user_id: str
    status: MembershipStatus = MembershipStatus.ACTIVE
    removed_at: datetime | None = None

    def _transition(self, target: MembershipStatus) -> None:
        allowed = _MEMBERSHIP_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Membership '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def activate(self) -> None:
        self._transition(MembershipStatus.ACTIVE)

    def remove(self) -> None:
        self._transition(MembershipStatus.REMOVED)
        self.removed_at = _now()


# -- MfaFactor -------------------------------------------------------------------------

_MFA_TRANSITIONS: dict[MfaFactorStatus, set[MfaFactorStatus]] = {
    MfaFactorStatus.PENDING: {MfaFactorStatus.ACTIVE, MfaFactorStatus.DISABLED},
    MfaFactorStatus.ACTIVE: {MfaFactorStatus.DISABLED},
    MfaFactorStatus.DISABLED: set(),
}


@dataclass
class MfaFactor:
    id: str
    user_id: str
    status: MfaFactorStatus = MfaFactorStatus.PENDING
    verified_at: datetime | None = None

    def _transition(self, target: MfaFactorStatus) -> None:
        allowed = _MFA_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"MfaFactor '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def verify(self) -> None:
        self._transition(MfaFactorStatus.ACTIVE)
        self.verified_at = _now()

    def disable(self) -> None:
        self._transition(MfaFactorStatus.DISABLED)
