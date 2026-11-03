"""Pure-Python domain entities with guarded state machines — no ORM
imports, mirroring every prior AIOS platform's domain layer. Five
job-style resources get a dedicated entity here (TestRun,
RegressionScan, PerformanceTestRun, ChaosExperiment,
CertificationRun); the remaining job-style resources (SecurityScan,
WorkflowValidationRun) share the identical queued -> running ->
completed/failed shape but are guarded directly in their service
instead, the same "simple status field" precedent used throughout
this platform family for resources whose lifecycle doesn't carry any
extra domain logic beyond the four states themselves."""
from __future__ import annotations

from dataclasses import dataclass

from quality_platform.core.exceptions import InvalidTransitionError
from quality_platform.domain.enums import JobStatus

_JOB_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.RUNNING},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
}


class _GuardedJob:
    """Shared transition-guard mixin for every job-style domain entity
    below — all five use the exact same queued -> running ->
    completed/failed graph, so the guard logic lives once here rather
    than being copy-pasted five times."""

    id: str
    status: JobStatus

    def _transition(self, target: JobStatus) -> None:
        allowed = _JOB_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"{type(self).__name__} '{self.id}' cannot transition from {self.status.value} to {target.value}"
            )
        self.status = target

    def start(self) -> None:
        self._transition(JobStatus.RUNNING)

    def complete(self) -> None:
        self._transition(JobStatus.COMPLETED)

    def fail(self) -> None:
        self._transition(JobStatus.FAILED)


@dataclass
class TestRun(_GuardedJob):
    id: str
    status: JobStatus = JobStatus.QUEUED


@dataclass
class RegressionScan(_GuardedJob):
    id: str
    status: JobStatus = JobStatus.QUEUED


@dataclass
class PerformanceTestRun(_GuardedJob):
    id: str
    status: JobStatus = JobStatus.QUEUED


@dataclass
class ChaosExperiment(_GuardedJob):
    id: str
    status: JobStatus = JobStatus.QUEUED


@dataclass
class CertificationRun(_GuardedJob):
    id: str
    status: JobStatus = JobStatus.QUEUED
