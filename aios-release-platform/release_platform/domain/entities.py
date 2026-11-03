"""Pure-Python domain entities with guarded state machines — no ORM
imports, so these are trivially unit-testable in isolation. Three
distinct transition graphs, matching how differently these three
resources actually behave in practice:

`Deployment` uses the generic `JobStatus` shape (queued -> in_progress
-> succeeded/failed, plus a post-hoc rolled_back marker) shared by
every prior AIOS platform's job-like resources.

`Release` has its own bespoke editorial-approval lifecycle (draft ->
candidate -> approved -> released -> deprecated/yanked) since release
governance semantics don't map onto generic start/complete/fail.

`Rollout` has its own bespoke progressive-execution lifecycle (planned
-> in_progress -> paused/completed/aborted, with pause being
resumable) since a rollout can be paused mid-flight in a way a
deployment job cannot.

Simpler status-only resources (feature flags, licenses, environments,
health check runs, rollbacks, SBOM/signature/approval records) are
guarded directly in-service instead, the same "simple status field"
precedent every prior platform established."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from release_platform.core.exceptions import InvalidTransitionError
from release_platform.domain.enums import JobStatus, ReleaseStatus, RolloutStatus
from release_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


# -- deployment (shared job lifecycle) ------------------------------------------------------------------

_DEPLOYMENT_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.IN_PROGRESS},
    JobStatus.IN_PROGRESS: {JobStatus.SUCCEEDED, JobStatus.FAILED},
    JobStatus.SUCCEEDED: {JobStatus.ROLLED_BACK},
    JobStatus.FAILED: set(),
    JobStatus.ROLLED_BACK: set(),
}


@dataclass
class Deployment:
    id: str
    tenant_id: str
    release_id: str
    environment_id: str
    target_type: str
    status: JobStatus = JobStatus.QUEUED
    failure_reason: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def _transition(self, target: JobStatus) -> None:
        allowed = _DEPLOYMENT_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Cannot transition deployment from '{self.status.value}' to '{target.value}'")
        self.status = target

    def start(self) -> None:
        self._transition(JobStatus.IN_PROGRESS)
        self.started_at = _now()

    def succeed(self) -> None:
        self._transition(JobStatus.SUCCEEDED)
        self.finished_at = _now()

    def fail(self, *, reason: str) -> None:
        self._transition(JobStatus.FAILED)
        self.failure_reason = reason
        self.finished_at = _now()

    def mark_rolled_back(self) -> None:
        self._transition(JobStatus.ROLLED_BACK)


# -- release (editorial-approval lifecycle) --------------------------------------------------------------

_RELEASE_TRANSITIONS: dict[ReleaseStatus, set[ReleaseStatus]] = {
    ReleaseStatus.DRAFT: {ReleaseStatus.CANDIDATE},
    ReleaseStatus.CANDIDATE: {ReleaseStatus.APPROVED, ReleaseStatus.DRAFT},
    ReleaseStatus.APPROVED: {ReleaseStatus.RELEASED, ReleaseStatus.CANDIDATE},
    ReleaseStatus.RELEASED: {ReleaseStatus.DEPRECATED, ReleaseStatus.YANKED},
    ReleaseStatus.DEPRECATED: set(),
    ReleaseStatus.YANKED: set(),
}


@dataclass
class Release:
    id: str
    tenant_id: str
    version: str
    channel: str
    status: ReleaseStatus = ReleaseStatus.DRAFT
    released_at: datetime | None = None

    def _transition(self, target: ReleaseStatus) -> None:
        allowed = _RELEASE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Cannot transition release from '{self.status.value}' to '{target.value}'")
        self.status = target

    def submit_for_candidate(self) -> None:
        self._transition(ReleaseStatus.CANDIDATE)

    def approve(self) -> None:
        self._transition(ReleaseStatus.APPROVED)

    def reject(self) -> None:
        self._transition(ReleaseStatus.DRAFT)

    def revoke_approval(self) -> None:
        self._transition(ReleaseStatus.CANDIDATE)

    def release(self) -> None:
        self._transition(ReleaseStatus.RELEASED)
        self.released_at = _now()

    def deprecate(self) -> None:
        self._transition(ReleaseStatus.DEPRECATED)

    def yank(self) -> None:
        self._transition(ReleaseStatus.YANKED)


# -- rollout (progressive-execution lifecycle) -------------------------------------------------------------

_ROLLOUT_TRANSITIONS: dict[RolloutStatus, set[RolloutStatus]] = {
    RolloutStatus.PLANNED: {RolloutStatus.IN_PROGRESS, RolloutStatus.ABORTED},
    RolloutStatus.IN_PROGRESS: {RolloutStatus.PAUSED, RolloutStatus.COMPLETED, RolloutStatus.ABORTED},
    RolloutStatus.PAUSED: {RolloutStatus.IN_PROGRESS, RolloutStatus.ABORTED},
    RolloutStatus.COMPLETED: set(),
    RolloutStatus.ABORTED: set(),
}


@dataclass
class Rollout:
    id: str
    tenant_id: str
    deployment_id: str
    strategy: str
    status: RolloutStatus = RolloutStatus.PLANNED
    current_step_pct: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def _transition(self, target: RolloutStatus) -> None:
        allowed = _ROLLOUT_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Cannot transition rollout from '{self.status.value}' to '{target.value}'")
        self.status = target

    def start(self) -> None:
        self._transition(RolloutStatus.IN_PROGRESS)
        self.started_at = _now()

    def pause(self) -> None:
        self._transition(RolloutStatus.PAUSED)

    def resume(self) -> None:
        self._transition(RolloutStatus.IN_PROGRESS)

    def advance(self, *, step_pct: float) -> None:
        if self.status != RolloutStatus.IN_PROGRESS:
            raise InvalidTransitionError(f"Cannot advance rollout while it is '{self.status.value}'")
        self.current_step_pct = min(max(step_pct, self.current_step_pct), 100.0)

    def complete(self) -> None:
        self._transition(RolloutStatus.COMPLETED)
        self.current_step_pct = 100.0
        self.completed_at = _now()

    def abort(self) -> None:
        self._transition(RolloutStatus.ABORTED)
