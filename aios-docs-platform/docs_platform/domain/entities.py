"""Pure-Python domain entities with guarded state machines — no ORM
imports, mirroring every other AIOS platform's domain layer.

Two distinct transition graphs live here: the shared `JobStatus`
queued -> running -> completed/failed shape (used only by
`GenerationJob` in this platform — automation runs are the sole
job-style resource), and `DocPage`'s richer editorial lifecycle
(draft -> in_review -> published -> archived/deprecated), which needs
its own graph and its own named methods since "submit for review" and
"publish" aren't interchangeable with "start"/"complete". The
remaining resources in this platform (reviews, enrollments, comments)
have simple status fields with no extra domain logic beyond a couple
of states, so — the same "simple status field" precedent used
throughout this platform family — they're guarded directly in their
service instead of getting a dedicated entity here."""
from __future__ import annotations

from dataclasses import dataclass

from docs_platform.core.exceptions import InvalidTransitionError
from docs_platform.domain.enums import DocPageStatus, JobStatus

_JOB_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.RUNNING},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
}


@dataclass
class GenerationJob:
    id: str
    status: JobStatus = JobStatus.QUEUED

    def _transition(self, target: JobStatus) -> None:
        allowed = _JOB_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"GenerationJob '{self.id}' cannot transition from {self.status.value} to {target.value}"
            )
        self.status = target

    def start(self) -> None:
        self._transition(JobStatus.RUNNING)

    def complete(self) -> None:
        self._transition(JobStatus.COMPLETED)

    def fail(self) -> None:
        self._transition(JobStatus.FAILED)


_DOC_PAGE_TRANSITIONS: dict[DocPageStatus, set[DocPageStatus]] = {
    DocPageStatus.DRAFT: {DocPageStatus.IN_REVIEW},
    DocPageStatus.IN_REVIEW: {DocPageStatus.PUBLISHED, DocPageStatus.DRAFT},
    DocPageStatus.PUBLISHED: {DocPageStatus.ARCHIVED, DocPageStatus.DEPRECATED},
    DocPageStatus.DEPRECATED: {DocPageStatus.ARCHIVED},
    DocPageStatus.ARCHIVED: set(),
}


@dataclass
class DocPage:
    id: str
    status: DocPageStatus = DocPageStatus.DRAFT

    def _transition(self, target: DocPageStatus) -> None:
        allowed = _DOC_PAGE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"DocPage '{self.id}' cannot transition from {self.status.value} to {target.value}"
            )
        self.status = target

    def submit_for_review(self) -> None:
        self._transition(DocPageStatus.IN_REVIEW)

    def publish(self) -> None:
        self._transition(DocPageStatus.PUBLISHED)

    def reject(self) -> None:
        """Sends an in-review page back to draft — the reviewer found
        problems and wants another pass, not a rewrite from a blank
        page (the content itself is untouched by this transition)."""
        self._transition(DocPageStatus.DRAFT)

    def archive(self) -> None:
        self._transition(DocPageStatus.ARCHIVED)

    def deprecate(self) -> None:
        self._transition(DocPageStatus.DEPRECATED)
