"""Pure-Python domain entities with guarded state-machine transitions.
No ORM imports here — these are the same shape every prior AIOS
platform used for its bespoke lifecycles, kept separate from the ORM
models so the transition rules are testable without a database.

Two entity shapes in this platform:

`BenchmarkRun` shares the generic job lifecycle every prior platform's
job-shaped resource uses: queued -> running -> completed/failed.

`Recommendation` has its own bespoke editorial-style lifecycle since a
cost/perf recommendation isn't a "job" — it's proposed by the
auto-optimization engine, then a human (or an automated policy) decides
whether to accept, reject, or apply it. Accepted recommendations can
still be applied later; rejected/expired are terminal.
"""
from __future__ import annotations

from dataclasses import dataclass

from perf_platform.core.exceptions import InvalidTransitionError
from perf_platform.domain.enums import JobStatus, RecommendationStatus

_JOB_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.RUNNING},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
}

_RECOMMENDATION_TRANSITIONS: dict[RecommendationStatus, set[RecommendationStatus]] = {
    RecommendationStatus.PROPOSED: {RecommendationStatus.ACCEPTED, RecommendationStatus.REJECTED, RecommendationStatus.EXPIRED},
    RecommendationStatus.ACCEPTED: {RecommendationStatus.APPLIED, RecommendationStatus.REJECTED},
    RecommendationStatus.APPLIED: set(),
    RecommendationStatus.REJECTED: set(),
    RecommendationStatus.EXPIRED: set(),
}


@dataclass
class BenchmarkRun:
    id: str
    status: JobStatus = JobStatus.QUEUED

    def _transition(self, target: JobStatus) -> None:
        allowed = _JOB_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"BenchmarkRun cannot move from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(JobStatus.RUNNING)

    def complete(self) -> None:
        self._transition(JobStatus.COMPLETED)

    def fail(self) -> None:
        self._transition(JobStatus.FAILED)


@dataclass
class Recommendation:
    id: str
    status: RecommendationStatus = RecommendationStatus.PROPOSED

    def _transition(self, target: RecommendationStatus) -> None:
        allowed = _RECOMMENDATION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Recommendation cannot move from {self.status.value} to {target.value}")
        self.status = target

    def accept(self) -> None:
        self._transition(RecommendationStatus.ACCEPTED)

    def reject(self) -> None:
        self._transition(RecommendationStatus.REJECTED)

    def apply(self) -> None:
        self._transition(RecommendationStatus.APPLIED)

    def expire(self) -> None:
        self._transition(RecommendationStatus.EXPIRED)
