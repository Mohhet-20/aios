"""Pure-Python domain aggregates — no ORM/SQLAlchemy imports here, the
same separation every prior AIOS platform uses. Each entity owns a
guarded `_transition()` over its own status enum (or, where the
lifecycle is really just a couple of independent boolean flags rather
than a status enum — comments, notifications — guarded flag-mutating
methods instead of a transition map)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from collaboration_platform.core.exceptions import (
    InvalidTransitionError,
    ReviewAlreadyDecidedError,
    ThreadAlreadyResolvedError,
)
from collaboration_platform.domain.enums import (
    AssetStatus,
    BranchStatus,
    ReviewStatus,
    TaskStatus,
    WorkspaceStatus,
)
from collaboration_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on DateTime round-trip; every timestamp this
    platform writes is UTC (`database.base.utcnow`), so a naive value
    reloaded from the database is safely treated as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# -- Workspace ------------------------------------------------------------------------

_WORKSPACE_TRANSITIONS: dict[WorkspaceStatus, set[WorkspaceStatus]] = {
    WorkspaceStatus.ACTIVE: {WorkspaceStatus.ARCHIVED},
    WorkspaceStatus.ARCHIVED: {WorkspaceStatus.ACTIVE},
}


@dataclass
class Workspace:
    id: str
    name: str
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    archived_at: datetime | None = None

    def _transition(self, target: WorkspaceStatus) -> None:
        allowed = _WORKSPACE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Workspace '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def archive(self) -> None:
        self._transition(WorkspaceStatus.ARCHIVED)
        self.archived_at = _now()

    def restore(self) -> None:
        self._transition(WorkspaceStatus.ACTIVE)
        self.archived_at = None


# -- CollaborationAsset ---------------------------------------------------------------

_ASSET_TRANSITIONS: dict[AssetStatus, set[AssetStatus]] = {
    AssetStatus.ACTIVE: {AssetStatus.ARCHIVED, AssetStatus.DELETED},
    AssetStatus.ARCHIVED: {AssetStatus.ACTIVE, AssetStatus.DELETED},
    AssetStatus.DELETED: set(),
}


@dataclass
class CollaborationAsset:
    id: str
    name: str
    status: AssetStatus = AssetStatus.ACTIVE
    archived_at: datetime | None = None
    deleted_at: datetime | None = None

    def _transition(self, target: AssetStatus) -> None:
        allowed = _ASSET_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Asset '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def archive(self) -> None:
        self._transition(AssetStatus.ARCHIVED)
        self.archived_at = _now()

    def restore(self) -> None:
        self._transition(AssetStatus.ACTIVE)
        self.archived_at = None

    def delete(self) -> None:
        self._transition(AssetStatus.DELETED)
        self.deleted_at = _now()


# -- Comment (thread) -------------------------------------------------------------------

@dataclass
class Comment:
    """A comment's lifecycle is two independent flags (resolved,
    pinned) plus a terminal soft-delete, not a single status enum —
    "resolved" and "pinned" can be true or false in any combination,
    which a single enum would force into an awkward cross-product of
    states. Deletion is still guarded and terminal: nothing can be
    mutated on a deleted comment."""
    id: str
    body: str
    is_resolved: bool = False
    is_pinned: bool = False
    is_deleted: bool = False
    edited_at: datetime | None = None
    resolved_at: datetime | None = None
    deleted_at: datetime | None = None

    def _require_alive(self) -> None:
        if self.is_deleted:
            raise InvalidTransitionError(f"Comment '{self.id}' has been deleted and can no longer be modified")

    def edit(self, new_body: str) -> None:
        self._require_alive()
        self.body = new_body
        self.edited_at = _now()

    def resolve(self) -> None:
        self._require_alive()
        if self.is_resolved:
            raise ThreadAlreadyResolvedError(f"Comment thread '{self.id}' is already resolved")
        self.is_resolved = True
        self.resolved_at = _now()

    def reopen(self) -> None:
        self._require_alive()
        self.is_resolved = False
        self.resolved_at = None

    def pin(self) -> None:
        self._require_alive()
        self.is_pinned = True

    def unpin(self) -> None:
        self._require_alive()
        self.is_pinned = False

    def soft_delete(self) -> None:
        self._require_alive()
        self.is_deleted = True
        self.deleted_at = _now()


# -- Branch -----------------------------------------------------------------------------

_BRANCH_TRANSITIONS: dict[BranchStatus, set[BranchStatus]] = {
    BranchStatus.OPEN: {BranchStatus.MERGED, BranchStatus.CLOSED},
    BranchStatus.MERGED: set(),
    BranchStatus.CLOSED: set(),
}


@dataclass
class Branch:
    id: str
    name: str
    status: BranchStatus = BranchStatus.OPEN
    closed_at: datetime | None = None

    def _transition(self, target: BranchStatus) -> None:
        allowed = _BRANCH_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Branch '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def mark_merged(self) -> None:
        self._transition(BranchStatus.MERGED)
        self.closed_at = _now()

    def close(self) -> None:
        self._transition(BranchStatus.CLOSED)
        self.closed_at = _now()


# -- ReviewRequest ------------------------------------------------------------------------

_REVIEW_TRANSITIONS: dict[ReviewStatus, set[ReviewStatus]] = {
    ReviewStatus.PENDING: {ReviewStatus.IN_REVIEW, ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.CANCELLED},
    ReviewStatus.IN_REVIEW: {ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.CANCELLED},
    ReviewStatus.APPROVED: set(),
    ReviewStatus.REJECTED: set(),
    ReviewStatus.CANCELLED: set(),
}


@dataclass
class ReviewRequest:
    id: str
    status: ReviewStatus = ReviewStatus.PENDING
    approvals_received: int = 0
    required_approvals: int = 1
    decided_at: datetime | None = None

    def _transition(self, target: ReviewStatus) -> None:
        allowed = _REVIEW_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ReviewRequest '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start_review(self) -> None:
        self._transition(ReviewStatus.IN_REVIEW)

    def record_approval(self) -> bool:
        """Increments the approval count and, if this crosses the
        required-approvals threshold, transitions to APPROVED and
        returns True. Returns False if more approvals are still
        needed — the caller decides whether that also means starting
        the IN_REVIEW state on the first approval."""
        if self.status in (ReviewStatus.PENDING,):
            self.start_review()
        if self.status != ReviewStatus.IN_REVIEW:
            raise ReviewAlreadyDecidedError(f"ReviewRequest '{self.id}' has already been decided ({self.status.value})")
        self.approvals_received += 1
        if self.approvals_received >= self.required_approvals:
            self._transition(ReviewStatus.APPROVED)
            self.decided_at = _now()
            return True
        return False

    def reject(self) -> None:
        if self.status not in (ReviewStatus.PENDING, ReviewStatus.IN_REVIEW):
            raise ReviewAlreadyDecidedError(f"ReviewRequest '{self.id}' has already been decided ({self.status.value})")
        self._transition(ReviewStatus.REJECTED)
        self.decided_at = _now()

    def cancel(self) -> None:
        self._transition(ReviewStatus.CANCELLED)
        self.decided_at = _now()


# -- Task -------------------------------------------------------------------------------

_TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.DONE, TaskStatus.TODO, TaskStatus.CANCELLED},
    TaskStatus.DONE: {TaskStatus.IN_PROGRESS},
    TaskStatus.CANCELLED: set(),
}


@dataclass
class Task:
    id: str
    title: str
    status: TaskStatus = TaskStatus.TODO
    completed_at: datetime | None = None

    def _transition(self, target: TaskStatus) -> None:
        allowed = _TASK_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Task '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(TaskStatus.IN_PROGRESS)

    def complete(self) -> None:
        self._transition(TaskStatus.DONE)
        self.completed_at = _now()

    def reopen(self) -> None:
        self._transition(TaskStatus.IN_PROGRESS)
        self.completed_at = None

    def cancel(self) -> None:
        self._transition(TaskStatus.CANCELLED)
