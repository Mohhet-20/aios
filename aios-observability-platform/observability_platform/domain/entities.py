"""Pure-Python domain aggregates — no ORM/SQLAlchemy imports here, the
same separation every prior AIOS platform uses. Each entity owns a
guarded `_transition()` over its own status enum."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from observability_platform.core.exceptions import (
    AlertAlreadyResolvedError,
    IncidentAlreadyClosedError,
    InvalidTransitionError,
)
from observability_platform.domain.enums import AlertStatus, IncidentStatus, MaintenanceWindowStatus
from observability_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on DateTime round-trip; every timestamp this
    platform writes is UTC (`database.base.utcnow`), so a naive value
    reloaded from the database is safely treated as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# -- Alert --------------------------------------------------------------------------

_ALERT_TRANSITIONS: dict[AlertStatus, set[AlertStatus]] = {
    AlertStatus.FIRING: {AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED, AlertStatus.SUPPRESSED},
    AlertStatus.ACKNOWLEDGED: {AlertStatus.RESOLVED, AlertStatus.SUPPRESSED},
    AlertStatus.SUPPRESSED: {AlertStatus.FIRING, AlertStatus.RESOLVED},
    AlertStatus.RESOLVED: set(),
}


@dataclass
class Alert:
    id: str
    status: AlertStatus = AlertStatus.FIRING
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    suppressed_until: datetime | None = None

    def _transition(self, target: AlertStatus) -> None:
        allowed = _ALERT_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"Alert '{self.id}' cannot transition from {self.status.value} to {target.value}"
            )
        self.status = target

    def acknowledge(self) -> None:
        self._transition(AlertStatus.ACKNOWLEDGED)
        self.acknowledged_at = _now()

    def resolve(self) -> None:
        if self.status == AlertStatus.RESOLVED:
            raise AlertAlreadyResolvedError(f"Alert '{self.id}' is already resolved")
        self._transition(AlertStatus.RESOLVED)
        self.resolved_at = _now()

    def suppress(self, until: datetime) -> None:
        self._transition(AlertStatus.SUPPRESSED)
        self.suppressed_until = until

    def unsuppress(self) -> None:
        self._transition(AlertStatus.FIRING)
        self.suppressed_until = None


# -- Incident -----------------------------------------------------------------------

_INCIDENT_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.OPEN: {IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED},
    IncidentStatus.INVESTIGATING: {IncidentStatus.IDENTIFIED, IncidentStatus.MONITORING, IncidentStatus.RESOLVED},
    IncidentStatus.IDENTIFIED: {IncidentStatus.MONITORING, IncidentStatus.RESOLVED, IncidentStatus.INVESTIGATING},
    IncidentStatus.MONITORING: {IncidentStatus.RESOLVED, IncidentStatus.INVESTIGATING},
    IncidentStatus.RESOLVED: {IncidentStatus.CLOSED, IncidentStatus.INVESTIGATING},  # reopen on regression
    IncidentStatus.CLOSED: set(),
}


@dataclass
class Incident:
    id: str
    status: IncidentStatus = IncidentStatus.OPEN
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None

    def _transition(self, target: IncidentStatus) -> None:
        allowed = _INCIDENT_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"Incident '{self.id}' cannot transition from {self.status.value} to {target.value}"
            )
        self.status = target

    def acknowledge(self) -> None:
        self._transition(IncidentStatus.INVESTIGATING)
        self.acknowledged_at = _now()

    def mark_identified(self) -> None:
        self._transition(IncidentStatus.IDENTIFIED)

    def mark_monitoring(self) -> None:
        self._transition(IncidentStatus.MONITORING)

    def resolve(self) -> None:
        self._transition(IncidentStatus.RESOLVED)
        self.resolved_at = _now()

    def reopen(self) -> None:
        if self.status != IncidentStatus.RESOLVED:
            raise InvalidTransitionError(f"Incident '{self.id}' can only be reopened from resolved")
        self._transition(IncidentStatus.INVESTIGATING)
        self.resolved_at = None

    def close(self) -> None:
        if self.status == IncidentStatus.CLOSED:
            raise IncidentAlreadyClosedError(f"Incident '{self.id}' is already closed")
        self._transition(IncidentStatus.CLOSED)
        self.closed_at = _now()


# -- MaintenanceWindow ----------------------------------------------------------------

_MW_TRANSITIONS: dict[MaintenanceWindowStatus, set[MaintenanceWindowStatus]] = {
    MaintenanceWindowStatus.SCHEDULED: {MaintenanceWindowStatus.ACTIVE, MaintenanceWindowStatus.CANCELLED},
    MaintenanceWindowStatus.ACTIVE: {MaintenanceWindowStatus.COMPLETED, MaintenanceWindowStatus.CANCELLED},
    MaintenanceWindowStatus.COMPLETED: set(),
    MaintenanceWindowStatus.CANCELLED: set(),
}


@dataclass
class MaintenanceWindow:
    id: str
    status: MaintenanceWindowStatus = MaintenanceWindowStatus.SCHEDULED

    def _transition(self, target: MaintenanceWindowStatus) -> None:
        allowed = _MW_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"MaintenanceWindow '{self.id}' cannot transition from {self.status.value} to {target.value}"
            )
        self.status = target

    def activate(self) -> None:
        self._transition(MaintenanceWindowStatus.ACTIVE)

    def complete(self) -> None:
        self._transition(MaintenanceWindowStatus.COMPLETED)

    def cancel(self) -> None:
        self._transition(MaintenanceWindowStatus.CANCELLED)
