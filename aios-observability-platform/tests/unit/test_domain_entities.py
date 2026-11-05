"""Direct unit tests of the guarded domain-entity state machines in
`domain/entities.py` — no database involved, just the pure-Python
transition logic. Mirrors the pattern established in every other AIOS
services's `tests/unit/test_domain_entities.py`."""
from __future__ import annotations

import pytest

from observability_platform.core.exceptions import (
    AlertAlreadyResolvedError,
    IncidentAlreadyClosedError,
    InvalidTransitionError,
)
from observability_platform.domain.entities import Alert, Incident, MaintenanceWindow
from observability_platform.domain.enums import AlertStatus, IncidentStatus, MaintenanceWindowStatus


def test_alert_happy_path_and_illegal_resolve_from_resolved():
    alert = Alert(id="a1")
    assert alert.status == AlertStatus.FIRING
    alert.acknowledge()
    assert alert.status == AlertStatus.ACKNOWLEDGED
    assert alert.acknowledged_at is not None
    alert.resolve()
    assert alert.status == AlertStatus.RESOLVED
    assert alert.resolved_at is not None
    with pytest.raises(AlertAlreadyResolvedError):
        alert.resolve()


def test_alert_suppress_and_unsuppress_cycle():
    from datetime import datetime, timedelta, timezone

    alert = Alert(id="a2")
    until = datetime.now(timezone.utc) + timedelta(hours=1)
    alert.suppress(until)
    assert alert.status == AlertStatus.SUPPRESSED
    assert alert.suppressed_until == until
    alert.unsuppress()
    assert alert.status == AlertStatus.FIRING
    assert alert.suppressed_until is None


def test_alert_cannot_acknowledge_after_resolved():
    alert = Alert(id="a3")
    alert.resolve()
    with pytest.raises(InvalidTransitionError):
        alert.acknowledge()


def test_incident_full_lifecycle():
    incident = Incident(id="i1")
    assert incident.status == IncidentStatus.OPEN
    incident.acknowledge()
    assert incident.status == IncidentStatus.INVESTIGATING
    incident.mark_identified()
    assert incident.status == IncidentStatus.IDENTIFIED
    incident.mark_monitoring()
    assert incident.status == IncidentStatus.MONITORING
    incident.resolve()
    assert incident.status == IncidentStatus.RESOLVED
    incident.close()
    assert incident.status == IncidentStatus.CLOSED
    with pytest.raises(IncidentAlreadyClosedError):
        incident.close()


def test_incident_reopen_only_from_resolved():
    incident = Incident(id="i2")
    with pytest.raises(InvalidTransitionError):
        incident.reopen()  # can't reopen from OPEN
    incident.resolve()
    incident.reopen()
    assert incident.status == IncidentStatus.INVESTIGATING
    assert incident.resolved_at is None


def test_incident_cannot_skip_straight_to_monitoring():
    incident = Incident(id="i3")
    with pytest.raises(InvalidTransitionError):
        incident.mark_monitoring()


def test_maintenance_window_lifecycle_and_illegal_transitions():
    window = MaintenanceWindow(id="m1")
    assert window.status == MaintenanceWindowStatus.SCHEDULED
    window.activate()
    assert window.status == MaintenanceWindowStatus.ACTIVE
    window.complete()
    assert window.status == MaintenanceWindowStatus.COMPLETED
    with pytest.raises(InvalidTransitionError):
        window.activate()  # terminal state


def test_maintenance_window_cancel_from_scheduled():
    window = MaintenanceWindow(id="m2")
    window.cancel()
    assert window.status == MaintenanceWindowStatus.CANCELLED
    with pytest.raises(InvalidTransitionError):
        window.cancel()
