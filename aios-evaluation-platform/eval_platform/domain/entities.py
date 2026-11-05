"""Pure-Python domain aggregates — no ORM/SQLAlchemy imports here, same
separation every other AIOS platform uses. `Evaluation` and `Dataset`
own their identity lifecycle (draft/active/deprecated/archived,
draft/published/archived); `EvaluationRun` and `BenchmarkRun` share the
same run-time state machine (`RunStatus`) since both are "execute
something against a dataset and score it," just with different result
shapes; `Alert` owns the open/acknowledge/resolve incident lifecycle."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from eval_platform.core.exceptions import InvalidTransitionError, ValidationError
from eval_platform.domain.enums import AlertStatus, DatasetStatus, EvaluationStatus, RunStatus
from eval_platform.clock import utc_now


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


# -- Evaluation --------------------------------------------------------------------

_EVALUATION_TRANSITIONS: dict[EvaluationStatus, set[EvaluationStatus]] = {
    EvaluationStatus.DRAFT: {EvaluationStatus.ACTIVE, EvaluationStatus.ARCHIVED},
    EvaluationStatus.ACTIVE: {EvaluationStatus.DEPRECATED, EvaluationStatus.ARCHIVED},
    EvaluationStatus.DEPRECATED: {EvaluationStatus.ACTIVE, EvaluationStatus.ARCHIVED},
    EvaluationStatus.ARCHIVED: set(),
}


@dataclass
class Evaluation:
    id: str
    workspace_id: str
    organization_id: str
    name: str
    slug: str
    owner_id: str
    category: str
    description: str | None = None
    tags: list = field(default_factory=list)
    status: EvaluationStatus = EvaluationStatus.DRAFT
    current_version_id: str | None = None
    eval_metadata: dict = field(default_factory=dict)

    def _transition(self, target: EvaluationStatus) -> None:
        allowed = _EVALUATION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Evaluation '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def activate(self, version_id: str) -> None:
        """Activating a new version of an already-ACTIVE/DEPRECATED
        evaluation just repoints `current_version_id`; activating an
        evaluation's first version (from DRAFT) also flips status."""
        if not version_id:
            raise ValidationError("cannot activate an evaluation without a version")
        if self.status in (EvaluationStatus.ACTIVE, EvaluationStatus.DEPRECATED):
            self.current_version_id = version_id
            self.status = EvaluationStatus.ACTIVE
            return
        self._transition(EvaluationStatus.ACTIVE)
        self.current_version_id = version_id

    def deprecate(self) -> None:
        self._transition(EvaluationStatus.DEPRECATED)

    def archive(self) -> None:
        self._transition(EvaluationStatus.ARCHIVED)


# -- Dataset -------------------------------------------------------------------------

_DATASET_TRANSITIONS: dict[DatasetStatus, set[DatasetStatus]] = {
    DatasetStatus.DRAFT: {DatasetStatus.PUBLISHED, DatasetStatus.ARCHIVED},
    DatasetStatus.PUBLISHED: {DatasetStatus.ARCHIVED},
    DatasetStatus.ARCHIVED: set(),
}


@dataclass
class Dataset:
    id: str
    workspace_id: str
    organization_id: str
    name: str
    slug: str
    owner_id: str
    dataset_type: str
    description: str | None = None
    tags: list = field(default_factory=list)
    status: DatasetStatus = DatasetStatus.DRAFT
    current_version_id: str | None = None
    lineage_parent_dataset_id: str | None = None
    dataset_metadata: dict = field(default_factory=dict)

    def _transition(self, target: DatasetStatus) -> None:
        allowed = _DATASET_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Dataset '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def publish(self, version_id: str) -> None:
        if not version_id:
            raise ValidationError("cannot publish a dataset without a version")
        self._transition(DatasetStatus.PUBLISHED)
        self.current_version_id = version_id

    def republish(self, version_id: str) -> None:
        """A new version of an already-PUBLISHED dataset just repoints
        `current_version_id` without a status transition."""
        if self.status != DatasetStatus.PUBLISHED:
            raise InvalidTransitionError(f"Dataset '{self.id}' must be PUBLISHED to republish (status: {self.status.value})")
        if not version_id:
            raise ValidationError("cannot republish a dataset without a version")
        self.current_version_id = version_id

    def archive(self) -> None:
        self._transition(DatasetStatus.ARCHIVED)


# -- Run (shared by EvaluationRun and BenchmarkRun) ---------------------------------

_RUN_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.PENDING: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RUNNING: {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.TIMED_OUT, RunStatus.CANCELLED},
    RunStatus.FAILED: {RunStatus.RUNNING},  # operator/engine-driven retry
    RunStatus.TIMED_OUT: {RunStatus.RUNNING},
    RunStatus.SUCCEEDED: set(),
    RunStatus.CANCELLED: set(),
}


class _RunMixin:
    """Shared transition machinery for EvaluationRun/BenchmarkRun — both
    are "execute something against a dataset, score it, retry on
    failure up to a budget" with identical status semantics, just
    different result payloads, so the state machine lives once here."""

    status: RunStatus
    attempt_number: int
    max_retries: int
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: float | None
    error_message: str | None

    def _label(self) -> str:
        raise NotImplementedError

    def _transition(self, target: RunStatus) -> None:
        allowed = _RUN_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"{self._label()} cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(RunStatus.RUNNING)
        self.started_at = _now()

    def succeed(self) -> None:
        self._transition(RunStatus.SUCCEEDED)
        self._finish()

    def fail(self, error_message: str) -> None:
        self._transition(RunStatus.FAILED)
        self.error_message = error_message
        self._finish()

    def timeout(self, error_message: str | None = None) -> None:
        self._transition(RunStatus.TIMED_OUT)
        self.error_message = error_message or self.error_message or "run exceeded its configured timeout"
        self._finish()

    def retry(self) -> None:
        if self.status not in (RunStatus.FAILED, RunStatus.TIMED_OUT):
            raise InvalidTransitionError(f"{self._label()} can only retry from FAILED/TIMED_OUT (status: {self.status.value})")
        if self.attempt_number > self.max_retries:
            raise InvalidTransitionError(f"{self._label()} has exhausted its {self.max_retries} configured retries")
        self.attempt_number += 1
        self._transition(RunStatus.RUNNING)
        self.started_at = _now()
        self.completed_at = None
        self.duration_ms = None

    def cancel(self) -> None:
        self._transition(RunStatus.CANCELLED)
        self._finish()

    def _finish(self) -> None:
        self.completed_at = _now()
        started_at = _aware(self.started_at)
        if started_at is not None:
            self.duration_ms = (self.completed_at - started_at).total_seconds() * 1000


@dataclass
class EvaluationRun(_RunMixin):
    id: str
    evaluation_id: str
    evaluation_version_id: str
    workspace_id: str
    status: RunStatus = RunStatus.PENDING
    attempt_number: int = 1
    max_retries: int = 0
    item_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    overall_score: float | None = None
    metric_summary: dict = field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None

    def _label(self) -> str:
        return f"EvaluationRun '{self.id}'"

    def record_results(self, *, item_count: int, passed_count: int, overall_score: float | None, metric_summary: dict) -> None:
        self.item_count = item_count
        self.passed_count = passed_count
        self.failed_count = item_count - passed_count
        self.overall_score = overall_score
        self.metric_summary = metric_summary


@dataclass
class BenchmarkRun(_RunMixin):
    id: str
    benchmark_id: str
    workspace_id: str
    status: RunStatus = RunStatus.PENDING
    attempt_number: int = 1
    max_retries: int = 0
    candidates: list = field(default_factory=list)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None

    def _label(self) -> str:
        return f"BenchmarkRun '{self.id}'"


# -- Alert -----------------------------------------------------------------------

_ALERT_TRANSITIONS: dict[AlertStatus, set[AlertStatus]] = {
    AlertStatus.OPEN: {AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED},
    AlertStatus.ACKNOWLEDGED: {AlertStatus.RESOLVED, AlertStatus.OPEN},
    AlertStatus.RESOLVED: set(),
}


@dataclass
class Alert:
    id: str
    workspace_id: str
    category: str
    severity: str
    message: str
    status: AlertStatus = AlertStatus.OPEN
    context: dict = field(default_factory=dict)
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None

    def _transition(self, target: AlertStatus) -> None:
        allowed = _ALERT_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Alert '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def acknowledge(self, *, by: str) -> None:
        self._transition(AlertStatus.ACKNOWLEDGED)
        self.acknowledged_by = by
        self.acknowledged_at = _now()

    def resolve(self, *, by: str) -> None:
        self._transition(AlertStatus.RESOLVED)
        self.resolved_by = by
        self.resolved_at = _now()

    def reopen(self) -> None:
        self._transition(AlertStatus.OPEN)
        self.acknowledged_by = None
        self.acknowledged_at = None
