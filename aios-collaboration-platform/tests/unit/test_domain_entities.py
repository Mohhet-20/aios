"""Pure-Python domain entity state-machine tests — no database, no
repositories, just the guarded transition logic in `domain/entities.py`
exercised directly. These are the fastest tests in the suite and the
first line of defense for lifecycle bugs before any service/API layer
gets involved."""
from __future__ import annotations

import pytest

from collaboration_platform.core.exceptions import (
    InvalidTransitionError,
    ReviewAlreadyDecidedError,
    ThreadAlreadyResolvedError,
)
from collaboration_platform.domain.entities import Branch, Comment, CollaborationAsset, ReviewRequest, Task, Workspace
from collaboration_platform.domain.enums import AssetStatus, BranchStatus, ReviewStatus, TaskStatus, WorkspaceStatus


def test_workspace_archive_restore_guarded():
    ws = Workspace(id="w1", name="Test")
    assert ws.status == WorkspaceStatus.ACTIVE
    with pytest.raises(InvalidTransitionError):
        ws.restore()  # already active
    ws.archive()
    assert ws.status == WorkspaceStatus.ARCHIVED
    assert ws.archived_at is not None
    with pytest.raises(InvalidTransitionError):
        ws.archive()  # already archived
    ws.restore()
    assert ws.status == WorkspaceStatus.ACTIVE
    assert ws.archived_at is None


def test_asset_lifecycle_terminal_delete():
    asset = CollaborationAsset(id="a1", name="Asset")
    asset.archive()
    assert asset.status == AssetStatus.ARCHIVED
    restored = asset
    restored.restore()
    assert restored.status == AssetStatus.ACTIVE
    asset.delete()
    assert asset.status == AssetStatus.DELETED
    assert asset.deleted_at is not None
    with pytest.raises(InvalidTransitionError):
        asset.restore()  # deleted is terminal
    with pytest.raises(InvalidTransitionError):
        asset.archive()


def test_comment_resolve_pin_delete_guards():
    comment = Comment(id="c1", body="hello")
    comment.resolve()
    assert comment.is_resolved is True
    with pytest.raises(ThreadAlreadyResolvedError):
        comment.resolve()
    comment.reopen()
    assert comment.is_resolved is False

    comment.pin()
    assert comment.is_pinned is True
    comment.unpin()
    assert comment.is_pinned is False

    comment.soft_delete()
    assert comment.is_deleted is True
    with pytest.raises(InvalidTransitionError):
        comment.edit("new text")
    with pytest.raises(InvalidTransitionError):
        comment.resolve()
    with pytest.raises(InvalidTransitionError):
        comment.pin()
    with pytest.raises(InvalidTransitionError):
        comment.soft_delete()


def test_branch_merge_and_close_are_terminal():
    branch = Branch(id="b1", name="feature-x")
    assert branch.status == BranchStatus.OPEN
    branch.mark_merged()
    assert branch.status == BranchStatus.MERGED
    assert branch.closed_at is not None
    with pytest.raises(InvalidTransitionError):
        branch.close()  # merged is terminal

    other = Branch(id="b2", name="feature-y")
    other.close()
    assert other.status == BranchStatus.CLOSED
    with pytest.raises(InvalidTransitionError):
        other.mark_merged()


def test_review_request_threshold_and_terminal_states():
    review = ReviewRequest(id="r1", required_approvals=2)
    assert review.status == ReviewStatus.PENDING
    assert review.record_approval() is False  # 1/2, not yet crossed
    assert review.status == ReviewStatus.IN_REVIEW
    assert review.record_approval() is True  # 2/2, crossed
    assert review.status == ReviewStatus.APPROVED
    assert review.decided_at is not None
    with pytest.raises(ReviewAlreadyDecidedError):
        review.record_approval()
    with pytest.raises(ReviewAlreadyDecidedError):
        review.reject()

    rejected = ReviewRequest(id="r2", required_approvals=1)
    rejected.reject()
    assert rejected.status == ReviewStatus.REJECTED
    with pytest.raises(ReviewAlreadyDecidedError):
        rejected.reject()

    cancelled = ReviewRequest(id="r3")
    cancelled.cancel()
    assert cancelled.status == ReviewStatus.CANCELLED


def test_task_lifecycle_transitions():
    task = Task(id="t1", title="Do the thing")
    assert task.status == TaskStatus.TODO
    task.start()
    assert task.status == TaskStatus.IN_PROGRESS
    task.complete()
    assert task.status == TaskStatus.DONE
    assert task.completed_at is not None
    with pytest.raises(InvalidTransitionError):
        task.cancel()  # done -> cancelled isn't legal
    task.reopen()
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.completed_at is None
    task.cancel()
    assert task.status == TaskStatus.CANCELLED
    with pytest.raises(InvalidTransitionError):
        task.start()  # cancelled is terminal
