"""Pure-Python domain aggregates — no ORM/SQLAlchemy imports here, the
same separation every other AIOS platform uses. Each entity owns a
guarded `_transition()` over its own status enum."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from security_platform.core.exceptions import (
    ApprovalAlreadyDecidedError,
    InvalidTransitionError,
)
from security_platform.domain.enums import (
    ApprovalStatus,
    PolicyStatus,
    SecretStatus,
    ThreatStatus,
    ViolationStatus,
)
from security_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on DateTime round-trip; every timestamp this
    platform writes is UTC (`database.base.utcnow`), so a naive value
    reloaded from the database is safely treated as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# -- Policy -----------------------------------------------------------------------

_POLICY_TRANSITIONS: dict[PolicyStatus, set[PolicyStatus]] = {
    PolicyStatus.DRAFT: {PolicyStatus.ACTIVE, PolicyStatus.ARCHIVED},
    PolicyStatus.ACTIVE: {PolicyStatus.DEPRECATED, PolicyStatus.ARCHIVED},
    PolicyStatus.DEPRECATED: {PolicyStatus.ACTIVE, PolicyStatus.ARCHIVED},
    PolicyStatus.ARCHIVED: set(),
}


@dataclass
class Policy:
    id: str
    status: PolicyStatus = PolicyStatus.DRAFT

    def _transition(self, target: PolicyStatus) -> None:
        allowed = _POLICY_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Policy '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def activate(self) -> None:
        self._transition(PolicyStatus.ACTIVE)

    def deprecate(self) -> None:
        self._transition(PolicyStatus.DEPRECATED)

    def archive(self) -> None:
        self._transition(PolicyStatus.ARCHIVED)


# -- GuardrailViolation ---------------------------------------------------------------

_VIOLATION_TRANSITIONS: dict[ViolationStatus, set[ViolationStatus]] = {
    ViolationStatus.OPEN: {ViolationStatus.ACKNOWLEDGED, ViolationStatus.RESOLVED},
    ViolationStatus.ACKNOWLEDGED: {ViolationStatus.RESOLVED},
    ViolationStatus.RESOLVED: set(),
}


@dataclass
class GuardrailViolation:
    id: str
    status: ViolationStatus = ViolationStatus.OPEN
    resolved_at: datetime | None = None

    def _transition(self, target: ViolationStatus) -> None:
        allowed = _VIOLATION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"GuardrailViolation '{self.id}' cannot transition from {self.status.value} to {target.value}"
            )
        self.status = target

    def acknowledge(self) -> None:
        self._transition(ViolationStatus.ACKNOWLEDGED)

    def resolve(self) -> None:
        self._transition(ViolationStatus.RESOLVED)
        self.resolved_at = _now()


# -- Secret -----------------------------------------------------------------------------

_SECRET_TRANSITIONS: dict[SecretStatus, set[SecretStatus]] = {
    SecretStatus.ACTIVE: {SecretStatus.ROTATING, SecretStatus.EXPIRED, SecretStatus.REVOKED},
    SecretStatus.ROTATING: {SecretStatus.ACTIVE, SecretStatus.REVOKED},
    SecretStatus.EXPIRED: {SecretStatus.REVOKED, SecretStatus.ACTIVE},  # renewed extends an expired secret back to active
    SecretStatus.REVOKED: set(),
}


@dataclass
class Secret:
    id: str
    status: SecretStatus = SecretStatus.ACTIVE

    def _transition(self, target: SecretStatus) -> None:
        allowed = _SECRET_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Secret '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start_rotation(self) -> None:
        self._transition(SecretStatus.ROTATING)

    def complete_rotation(self) -> None:
        self._transition(SecretStatus.ACTIVE)

    def expire(self) -> None:
        self._transition(SecretStatus.EXPIRED)

    def renew(self) -> None:
        self._transition(SecretStatus.ACTIVE)

    def revoke(self) -> None:
        self._transition(SecretStatus.REVOKED)


# -- ThreatDetection ------------------------------------------------------------------------

_THREAT_TRANSITIONS: dict[ThreatStatus, set[ThreatStatus]] = {
    ThreatStatus.DETECTED: {ThreatStatus.INVESTIGATING, ThreatStatus.DISMISSED, ThreatStatus.CONFIRMED},
    ThreatStatus.INVESTIGATING: {ThreatStatus.CONFIRMED, ThreatStatus.DISMISSED},
    ThreatStatus.CONFIRMED: {ThreatStatus.MITIGATED},
    ThreatStatus.MITIGATED: set(),
    ThreatStatus.DISMISSED: set(),
}


@dataclass
class ThreatDetection:
    id: str
    status: ThreatStatus = ThreatStatus.DETECTED
    resolved_at: datetime | None = None

    def _transition(self, target: ThreatStatus) -> None:
        allowed = _THREAT_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"ThreatDetection '{self.id}' cannot transition from {self.status.value} to {target.value}"
            )
        self.status = target

    def investigate(self) -> None:
        self._transition(ThreatStatus.INVESTIGATING)

    def confirm(self) -> None:
        self._transition(ThreatStatus.CONFIRMED)

    def dismiss(self) -> None:
        self._transition(ThreatStatus.DISMISSED)
        self.resolved_at = _now()

    def mitigate(self) -> None:
        self._transition(ThreatStatus.MITIGATED)
        self.resolved_at = _now()


# -- ApprovalRequest ---------------------------------------------------------------------------

_APPROVAL_TRANSITIONS: dict[ApprovalStatus, set[ApprovalStatus]] = {
    ApprovalStatus.PENDING: {ApprovalStatus.IN_REVIEW, ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.CANCELLED},
    ApprovalStatus.IN_REVIEW: {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.CANCELLED},
    ApprovalStatus.APPROVED: set(),
    ApprovalStatus.REJECTED: set(),
    ApprovalStatus.CANCELLED: set(),
}


@dataclass
class ApprovalRequest:
    id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approvals_received: int = 0
    required_approvals: int = 1
    decided_at: datetime | None = None

    def _transition(self, target: ApprovalStatus) -> None:
        allowed = _APPROVAL_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"ApprovalRequest '{self.id}' cannot transition from {self.status.value} to {target.value}"
            )
        self.status = target

    def start_review(self) -> None:
        self._transition(ApprovalStatus.IN_REVIEW)

    def record_approval(self) -> bool:
        """Increments the approval count and, if this crosses the
        required-approvals threshold, transitions to APPROVED and
        returns True; otherwise returns False."""
        if self.status == ApprovalStatus.PENDING:
            self.start_review()
        if self.status != ApprovalStatus.IN_REVIEW:
            raise ApprovalAlreadyDecidedError(f"ApprovalRequest '{self.id}' has already been decided ({self.status.value})")
        self.approvals_received += 1
        if self.approvals_received >= self.required_approvals:
            self._transition(ApprovalStatus.APPROVED)
            self.decided_at = _now()
            return True
        return False

    def reject(self) -> None:
        if self.status not in (ApprovalStatus.PENDING, ApprovalStatus.IN_REVIEW):
            raise ApprovalAlreadyDecidedError(f"ApprovalRequest '{self.id}' has already been decided ({self.status.value})")
        self._transition(ApprovalStatus.REJECTED)
        self.decided_at = _now()

    def cancel(self) -> None:
        self._transition(ApprovalStatus.CANCELLED)
        self.decided_at = _now()
