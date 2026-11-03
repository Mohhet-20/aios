"""Pure-Python domain aggregates — no ORM/SQLAlchemy imports here, same
separation every prior AIOS platform used. `Tool` owns the
publish/deprecate/disable lifecycle; `ToolExecution` owns the real
run-time retry/timeout/cancel/rollback state machine (the core of the
execution engine); `PluginInstallation` owns install/enable/disable/
update lifecycle; `Credential` owns rotate/expire/revoke; `Schedule`
owns trigger lifecycle (identical shape to the Workflow Engine's, scoped
to a tool instead of a workflow)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from tool_platform.core.exceptions import InvalidTransitionError, ValidationError
from tool_platform.domain.enums import (
    CredentialStatus,
    ExecutionStatus,
    PluginInstallationStatus,
    ScheduleStatus,
    ToolStatus,
)
from tool_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on DateTime round-trip; every timestamp this
    platform writes is UTC (`database.base.utcnow`), so a naive value
    reloaded from the database is safely treated as UTC rather than left
    to blow up a subtraction against a freshly-created aware datetime."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# -- Tool -----------------------------------------------------------------------

_TOOL_TRANSITIONS: dict[ToolStatus, set[ToolStatus]] = {
    ToolStatus.DRAFT: {ToolStatus.PUBLISHED, ToolStatus.DISABLED},
    ToolStatus.PUBLISHED: {ToolStatus.DEPRECATED, ToolStatus.DISABLED},
    ToolStatus.DEPRECATED: {ToolStatus.DISABLED, ToolStatus.PUBLISHED},
    ToolStatus.DISABLED: {ToolStatus.PUBLISHED, ToolStatus.DEPRECATED},
}


@dataclass
class Tool:
    id: str
    workspace_id: str
    organization_id: str
    name: str
    slug: str
    owner_id: str
    category: str
    description: str | None = None
    author: str | None = None
    tags: list = field(default_factory=list)
    status: ToolStatus = ToolStatus.DRAFT
    current_version_id: str | None = None
    tool_metadata: dict = field(default_factory=dict)

    def _transition(self, target: ToolStatus) -> None:
        allowed = _TOOL_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Tool '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def publish(self, version_id: str) -> None:
        """Publishing a new version of an already-PUBLISHED/DEPRECATED tool
        just repoints `current_version_id`; publishing a tool's first
        version (from DRAFT) also flips status to PUBLISHED."""
        if not version_id:
            raise ValidationError("cannot publish a tool without a version")
        if self.status in (ToolStatus.PUBLISHED, ToolStatus.DEPRECATED):
            self.current_version_id = version_id
            self.status = ToolStatus.PUBLISHED
            return
        self._transition(ToolStatus.PUBLISHED)
        self.current_version_id = version_id

    def deprecate(self) -> None:
        self._transition(ToolStatus.DEPRECATED)

    def disable(self) -> None:
        self._transition(ToolStatus.DISABLED)

    def enable(self) -> None:
        if self.status != ToolStatus.DISABLED:
            raise InvalidTransitionError(f"Tool '{self.id}' can only enable from DISABLED (status: {self.status.value})")
        self._transition(ToolStatus.PUBLISHED)


# -- ToolExecution ----------------------------------------------------------------

_EXECUTION_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {ExecutionStatus.QUEUED, ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED},
    ExecutionStatus.QUEUED: {ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED},
    ExecutionStatus.RUNNING: {
        ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT, ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.FAILED: {ExecutionStatus.RETRYING, ExecutionStatus.ROLLED_BACK},
    ExecutionStatus.TIMED_OUT: {ExecutionStatus.RETRYING, ExecutionStatus.ROLLED_BACK},
    ExecutionStatus.RETRYING: {ExecutionStatus.RUNNING, ExecutionStatus.FAILED},
    ExecutionStatus.SUCCEEDED: set(),
    ExecutionStatus.CANCELLED: set(),
    ExecutionStatus.ROLLED_BACK: set(),
}


@dataclass
class ToolExecution:
    id: str
    tool_id: str
    tool_version_id: str
    workspace_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    attempt_number: int = 1
    max_retries: int = 2
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None

    def _transition(self, target: ExecutionStatus) -> None:
        allowed = _EXECUTION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ToolExecution '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def queue(self) -> None:
        self._transition(ExecutionStatus.QUEUED)

    def start(self) -> None:
        self._transition(ExecutionStatus.RUNNING)
        self.started_at = _now()

    def succeed(self, output_data: dict | None = None) -> None:
        self._transition(ExecutionStatus.SUCCEEDED)
        if output_data is not None:
            self.output_data = output_data
        self._finish()

    def fail(self, error_message: str) -> None:
        self._transition(ExecutionStatus.FAILED)
        self.error_message = error_message
        self._finish()

    def timeout(self, error_message: str | None = None) -> None:
        self._transition(ExecutionStatus.TIMED_OUT)
        self.error_message = error_message or self.error_message or "tool call exceeded its configured timeout"
        self._finish()

    def retry(self) -> None:
        if self.status not in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT):
            raise InvalidTransitionError(f"ToolExecution '{self.id}' can only retry from FAILED/TIMED_OUT (status: {self.status.value})")
        if self.attempt_number > self.max_retries:
            raise InvalidTransitionError(f"ToolExecution '{self.id}' has exhausted its {self.max_retries} configured retries")
        self._transition(ExecutionStatus.RETRYING)
        self.attempt_number += 1

    def resume_after_retry(self) -> None:
        if self.status != ExecutionStatus.RETRYING:
            raise InvalidTransitionError(f"ToolExecution '{self.id}' must be RETRYING to resume (status: {self.status.value})")
        self._transition(ExecutionStatus.RUNNING)
        self.started_at = _now()

    def exhaust_retries(self, error_message: str) -> None:
        if self.status != ExecutionStatus.RETRYING:
            raise InvalidTransitionError(f"ToolExecution '{self.id}' must be RETRYING to exhaust (status: {self.status.value})")
        self._transition(ExecutionStatus.FAILED)
        self.error_message = error_message
        self._finish()

    def rollback(self) -> None:
        if self.status not in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT):
            raise InvalidTransitionError(f"ToolExecution '{self.id}' can only roll back from FAILED/TIMED_OUT (status: {self.status.value})")
        self._transition(ExecutionStatus.ROLLED_BACK)

    def cancel(self) -> None:
        self._transition(ExecutionStatus.CANCELLED)
        self._finish()

    def _finish(self) -> None:
        self.completed_at = _now()
        started_at = _aware(self.started_at)
        if started_at is not None:
            self.duration_ms = (self.completed_at - started_at).total_seconds() * 1000


# -- PluginInstallation ------------------------------------------------------------

_PLUGIN_INSTALLATION_TRANSITIONS: dict[PluginInstallationStatus, set[PluginInstallationStatus]] = {
    PluginInstallationStatus.INSTALLED: {
        PluginInstallationStatus.ENABLED, PluginInstallationStatus.UPDATING, PluginInstallationStatus.UNINSTALLED,
    },
    PluginInstallationStatus.ENABLED: {
        PluginInstallationStatus.DISABLED, PluginInstallationStatus.UPDATING, PluginInstallationStatus.UNINSTALLED,
    },
    PluginInstallationStatus.DISABLED: {
        PluginInstallationStatus.ENABLED, PluginInstallationStatus.UPDATING, PluginInstallationStatus.UNINSTALLED,
    },
    PluginInstallationStatus.UPDATING: {
        PluginInstallationStatus.ENABLED, PluginInstallationStatus.DISABLED, PluginInstallationStatus.FAILED,
    },
    PluginInstallationStatus.FAILED: {PluginInstallationStatus.UPDATING, PluginInstallationStatus.UNINSTALLED},
    PluginInstallationStatus.UNINSTALLED: set(),
}


@dataclass
class PluginInstallation:
    id: str
    plugin_id: str
    workspace_id: str
    installed_version: str
    installed_by: str
    status: PluginInstallationStatus = PluginInstallationStatus.INSTALLED
    configuration: dict = field(default_factory=dict)

    def _transition(self, target: PluginInstallationStatus) -> None:
        allowed = _PLUGIN_INSTALLATION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"PluginInstallation '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def enable(self) -> None:
        self._transition(PluginInstallationStatus.ENABLED)

    def disable(self) -> None:
        self._transition(PluginInstallationStatus.DISABLED)

    def begin_update(self) -> None:
        self._transition(PluginInstallationStatus.UPDATING)

    def complete_update(self, new_version: str, *, was_enabled: bool) -> None:
        if self.status != PluginInstallationStatus.UPDATING:
            raise InvalidTransitionError(f"PluginInstallation '{self.id}' must be UPDATING to complete an update (status: {self.status.value})")
        self.installed_version = new_version
        self._transition(PluginInstallationStatus.ENABLED if was_enabled else PluginInstallationStatus.DISABLED)

    def fail_update(self, error_message: str) -> None:
        self._transition(PluginInstallationStatus.FAILED)
        self.configuration = {**self.configuration, "last_update_error": error_message}

    def uninstall(self) -> None:
        self._transition(PluginInstallationStatus.UNINSTALLED)


# -- Credential ---------------------------------------------------------------------

_CREDENTIAL_TRANSITIONS: dict[CredentialStatus, set[CredentialStatus]] = {
    CredentialStatus.ACTIVE: {CredentialStatus.ROTATING, CredentialStatus.EXPIRED, CredentialStatus.REVOKED},
    CredentialStatus.ROTATING: {CredentialStatus.ACTIVE, CredentialStatus.EXPIRED, CredentialStatus.REVOKED},
    CredentialStatus.EXPIRED: {CredentialStatus.ROTATING, CredentialStatus.REVOKED},
    CredentialStatus.REVOKED: set(),
}


@dataclass
class Credential:
    id: str
    workspace_id: str
    name: str
    credential_type: str
    owner_id: str
    status: CredentialStatus = CredentialStatus.ACTIVE
    expires_at: datetime | None = None
    rotated_at: datetime | None = None

    def _transition(self, target: CredentialStatus) -> None:
        allowed = _CREDENTIAL_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Credential '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def begin_rotation(self) -> None:
        self._transition(CredentialStatus.ROTATING)

    def complete_rotation(self, *, new_expires_at: datetime | None = None) -> None:
        if self.status != CredentialStatus.ROTATING:
            raise InvalidTransitionError(f"Credential '{self.id}' must be ROTATING to complete a rotation (status: {self.status.value})")
        self._transition(CredentialStatus.ACTIVE)
        self.rotated_at = _now()
        if new_expires_at is not None:
            self.expires_at = new_expires_at

    def check_expiry(self, *, as_of: datetime | None = None) -> bool:
        """Idempotent: safe to call repeatedly from a sweep. Returns True
        if this call caused an ACTIVE/ROTATING credential to expire."""
        moment = as_of or _now()
        expires_at = _aware(self.expires_at)
        if expires_at is None or moment < expires_at:
            return False
        if self.status in (CredentialStatus.ACTIVE, CredentialStatus.ROTATING):
            self._transition(CredentialStatus.EXPIRED)
            return True
        return False

    def revoke(self) -> None:
        self._transition(CredentialStatus.REVOKED)


# -- Schedule -------------------------------------------------------------------------
# Identical shape to the Workflow Engine's Schedule entity — scoped to a
# tool instead of a workflow, same reasoning for every transition.

_SCHEDULE_TRANSITIONS: dict[ScheduleStatus, set[ScheduleStatus]] = {
    ScheduleStatus.ACTIVE: {ScheduleStatus.PAUSED, ScheduleStatus.CANCELLED, ScheduleStatus.COMPLETED},
    ScheduleStatus.PAUSED: {ScheduleStatus.ACTIVE, ScheduleStatus.CANCELLED},
    ScheduleStatus.COMPLETED: set(),
    ScheduleStatus.CANCELLED: set(),
}


@dataclass
class Schedule:
    id: str
    tool_id: str
    workspace_id: str
    schedule_type: str
    created_by: str
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    cron_expression: str | None = None
    interval_seconds: int | None = None
    run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    run_count: int = 0

    def _transition(self, target: ScheduleStatus) -> None:
        allowed = _SCHEDULE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Schedule '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def pause(self) -> None:
        self._transition(ScheduleStatus.PAUSED)

    def resume(self) -> None:
        if self.status != ScheduleStatus.PAUSED:
            raise InvalidTransitionError(f"Schedule '{self.id}' can only resume from PAUSED (status: {self.status.value})")
        self._transition(ScheduleStatus.ACTIVE)

    def cancel(self) -> None:
        self._transition(ScheduleStatus.CANCELLED)

    def complete(self) -> None:
        self._transition(ScheduleStatus.COMPLETED)

    def record_run(self, *, next_run_at: datetime | None) -> None:
        if self.status != ScheduleStatus.ACTIVE:
            raise InvalidTransitionError(f"Schedule '{self.id}' must be ACTIVE to record a run (status: {self.status.value})")
        self.last_run_at = _now()
        self.run_count += 1
        self.next_run_at = next_run_at
        if next_run_at is None:
            self.complete()
