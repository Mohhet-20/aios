"""Pure-Python domain aggregates — no ORM/SQLAlchemy imports here, the
same separation every other AIOS platform uses. Each entity owns a
guarded `_transition()` over its own status enum."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from infra_platform.core.exceptions import InvalidTransitionError
from infra_platform.domain.enums import (
    BackupStatus,
    ClusterStatus,
    DeploymentStatus,
    ImageStatus,
    ModelStage,
    PipelineRunStatus,
    RecoveryStatus,
    RunStatus,
)
from infra_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on DateTime round-trip; every timestamp this
    platform writes is UTC (`database.base.utcnow`), so a naive value
    reloaded from the database is safely treated as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# -- ContainerImage -----------------------------------------------------------------------

_IMAGE_TRANSITIONS: dict[ImageStatus, set[ImageStatus]] = {
    ImageStatus.BUILDING: {ImageStatus.SCANNING},
    ImageStatus.SCANNING: {ImageStatus.SIGNED, ImageStatus.SCAN_FAILED},
    ImageStatus.SIGNED: {ImageStatus.PUBLISHED},
    ImageStatus.PUBLISHED: {ImageStatus.DEPRECATED, ImageStatus.QUARANTINED},
    ImageStatus.DEPRECATED: {ImageStatus.QUARANTINED},
    ImageStatus.SCAN_FAILED: {ImageStatus.BUILDING, ImageStatus.QUARANTINED},
    ImageStatus.QUARANTINED: set(),
}


@dataclass
class ContainerImage:
    id: str
    status: ImageStatus = ImageStatus.BUILDING

    def _transition(self, target: ImageStatus) -> None:
        allowed = _IMAGE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ContainerImage '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start_scan(self) -> None:
        self._transition(ImageStatus.SCANNING)

    def mark_scan_failed(self) -> None:
        self._transition(ImageStatus.SCAN_FAILED)

    def mark_signed(self) -> None:
        self._transition(ImageStatus.SIGNED)

    def publish(self) -> None:
        self._transition(ImageStatus.PUBLISHED)

    def deprecate(self) -> None:
        self._transition(ImageStatus.DEPRECATED)

    def quarantine(self) -> None:
        self._transition(ImageStatus.QUARANTINED)

    def retry_build(self) -> None:
        self._transition(ImageStatus.BUILDING)


# -- PipelineRun ----------------------------------------------------------------------------

_PIPELINE_RUN_TRANSITIONS: dict[PipelineRunStatus, set[PipelineRunStatus]] = {
    PipelineRunStatus.PENDING: {PipelineRunStatus.RUNNING, PipelineRunStatus.CANCELLED},
    PipelineRunStatus.RUNNING: {PipelineRunStatus.SUCCEEDED, PipelineRunStatus.FAILED, PipelineRunStatus.CANCELLED},
    PipelineRunStatus.SUCCEEDED: set(),
    PipelineRunStatus.FAILED: set(),
    PipelineRunStatus.CANCELLED: set(),
}


@dataclass
class PipelineRun:
    id: str
    status: PipelineRunStatus = PipelineRunStatus.PENDING
    finished_at: datetime | None = None

    def _transition(self, target: PipelineRunStatus) -> None:
        allowed = _PIPELINE_RUN_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"PipelineRun '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(PipelineRunStatus.RUNNING)

    def succeed(self) -> None:
        self._transition(PipelineRunStatus.SUCCEEDED)
        self.finished_at = _now()

    def fail(self) -> None:
        self._transition(PipelineRunStatus.FAILED)
        self.finished_at = _now()

    def cancel(self) -> None:
        self._transition(PipelineRunStatus.CANCELLED)
        self.finished_at = _now()


# -- ModelVersion ---------------------------------------------------------------------------

_MODEL_STAGE_TRANSITIONS: dict[ModelStage, set[ModelStage]] = {
    ModelStage.DEVELOPMENT: {ModelStage.STAGING, ModelStage.ARCHIVED},
    ModelStage.STAGING: {ModelStage.PRODUCTION, ModelStage.ARCHIVED},
    ModelStage.PRODUCTION: {ModelStage.ARCHIVED},
    ModelStage.ARCHIVED: set(),
}


@dataclass
class ModelVersion:
    id: str
    stage: ModelStage = ModelStage.DEVELOPMENT

    def _transition(self, target: ModelStage) -> None:
        allowed = _MODEL_STAGE_TRANSITIONS.get(self.stage, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ModelVersion '{self.id}' cannot transition from {self.stage.value} to {target.value}")
        self.stage = target

    def promote_to_staging(self) -> None:
        self._transition(ModelStage.STAGING)

    def promote_to_production(self) -> None:
        self._transition(ModelStage.PRODUCTION)

    def archive(self) -> None:
        self._transition(ModelStage.ARCHIVED)


# -- ExperimentRun --------------------------------------------------------------------------

_RUN_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.RUNNING: {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.KILLED},
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
    RunStatus.KILLED: set(),
}


@dataclass
class ExperimentRun:
    id: str
    status: RunStatus = RunStatus.RUNNING
    finished_at: datetime | None = None

    def _transition(self, target: RunStatus) -> None:
        allowed = _RUN_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ExperimentRun '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def complete(self) -> None:
        self._transition(RunStatus.COMPLETED)
        self.finished_at = _now()

    def fail(self) -> None:
        self._transition(RunStatus.FAILED)
        self.finished_at = _now()

    def kill(self) -> None:
        self._transition(RunStatus.KILLED)
        self.finished_at = _now()


# -- Deployment -----------------------------------------------------------------------------

_DEPLOYMENT_TRANSITIONS: dict[DeploymentStatus, set[DeploymentStatus]] = {
    DeploymentStatus.PENDING: {DeploymentStatus.IN_PROGRESS},
    DeploymentStatus.IN_PROGRESS: {DeploymentStatus.SUCCEEDED, DeploymentStatus.FAILED, DeploymentStatus.PAUSED, DeploymentStatus.ROLLED_BACK},
    DeploymentStatus.PAUSED: {DeploymentStatus.IN_PROGRESS, DeploymentStatus.ROLLED_BACK},
    DeploymentStatus.SUCCEEDED: {DeploymentStatus.ROLLED_BACK},
    DeploymentStatus.FAILED: {DeploymentStatus.ROLLED_BACK},
    DeploymentStatus.ROLLED_BACK: set(),
}


@dataclass
class Deployment:
    id: str
    status: DeploymentStatus = DeploymentStatus.PENDING
    finished_at: datetime | None = None

    def _transition(self, target: DeploymentStatus) -> None:
        allowed = _DEPLOYMENT_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Deployment '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(DeploymentStatus.IN_PROGRESS)

    def pause(self) -> None:
        self._transition(DeploymentStatus.PAUSED)

    def resume(self) -> None:
        self._transition(DeploymentStatus.IN_PROGRESS)

    def succeed(self) -> None:
        self._transition(DeploymentStatus.SUCCEEDED)
        self.finished_at = _now()

    def fail(self) -> None:
        self._transition(DeploymentStatus.FAILED)
        self.finished_at = _now()

    def rollback(self) -> None:
        self._transition(DeploymentStatus.ROLLED_BACK)
        self.finished_at = _now()


# -- Cluster ----------------------------------------------------------------------------------

_CLUSTER_TRANSITIONS: dict[ClusterStatus, set[ClusterStatus]] = {
    ClusterStatus.PROVISIONING: {ClusterStatus.HEALTHY, ClusterStatus.UNHEALTHY},
    ClusterStatus.HEALTHY: {ClusterStatus.DEGRADED, ClusterStatus.UNHEALTHY, ClusterStatus.DECOMMISSIONED},
    ClusterStatus.DEGRADED: {ClusterStatus.HEALTHY, ClusterStatus.UNHEALTHY, ClusterStatus.DECOMMISSIONED},
    ClusterStatus.UNHEALTHY: {ClusterStatus.DEGRADED, ClusterStatus.HEALTHY, ClusterStatus.DECOMMISSIONED},
    ClusterStatus.DECOMMISSIONED: set(),
}


@dataclass
class Cluster:
    id: str
    status: ClusterStatus = ClusterStatus.PROVISIONING

    def _transition(self, target: ClusterStatus) -> None:
        allowed = _CLUSTER_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Cluster '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def mark_healthy(self) -> None:
        self._transition(ClusterStatus.HEALTHY)

    def mark_degraded(self) -> None:
        self._transition(ClusterStatus.DEGRADED)

    def mark_unhealthy(self) -> None:
        self._transition(ClusterStatus.UNHEALTHY)

    def decommission(self) -> None:
        self._transition(ClusterStatus.DECOMMISSIONED)


# -- Backup -----------------------------------------------------------------------------------

_BACKUP_TRANSITIONS: dict[BackupStatus, set[BackupStatus]] = {
    BackupStatus.PENDING: {BackupStatus.IN_PROGRESS},
    BackupStatus.IN_PROGRESS: {BackupStatus.COMPLETED, BackupStatus.FAILED},
    BackupStatus.COMPLETED: set(),
    BackupStatus.FAILED: set(),
}


@dataclass
class Backup:
    id: str
    status: BackupStatus = BackupStatus.PENDING
    completed_at: datetime | None = None

    def _transition(self, target: BackupStatus) -> None:
        allowed = _BACKUP_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Backup '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(BackupStatus.IN_PROGRESS)

    def complete(self) -> None:
        self._transition(BackupStatus.COMPLETED)
        self.completed_at = _now()

    def fail(self) -> None:
        self._transition(BackupStatus.FAILED)
        self.completed_at = _now()


# -- RecoveryExecution --------------------------------------------------------------------------

_RECOVERY_TRANSITIONS: dict[RecoveryStatus, set[RecoveryStatus]] = {
    RecoveryStatus.INITIATED: {RecoveryStatus.IN_PROGRESS, RecoveryStatus.FAILED},
    RecoveryStatus.IN_PROGRESS: {RecoveryStatus.COMPLETED, RecoveryStatus.FAILED},
    RecoveryStatus.COMPLETED: set(),
    RecoveryStatus.FAILED: set(),
}


@dataclass
class RecoveryExecution:
    id: str
    status: RecoveryStatus = RecoveryStatus.INITIATED
    completed_at: datetime | None = None

    def _transition(self, target: RecoveryStatus) -> None:
        allowed = _RECOVERY_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"RecoveryExecution '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(RecoveryStatus.IN_PROGRESS)

    def complete(self) -> None:
        self._transition(RecoveryStatus.COMPLETED)
        self.completed_at = _now()

    def fail(self) -> None:
        self._transition(RecoveryStatus.FAILED)
        self.completed_at = _now()
