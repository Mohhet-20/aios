from datetime import datetime, timedelta, timezone

import pytest

from memory_platform.core.exceptions import InvalidTransitionError, ValidationError
from memory_platform.domain.entities import KnowledgeItem, MemoryEntry
from memory_platform.domain.enums import KnowledgeItemStatus, MemoryStatus


def _entry(**overrides) -> MemoryEntry:
    defaults = dict(
        id="m1", workspace_id="ws1", memory_type="semantic", scope_type="agent", scope_id="agent1",
        content="the sky is blue",
    )
    defaults.update(overrides)
    return MemoryEntry(**defaults)


def _item(**overrides) -> KnowledgeItem:
    defaults = dict(id="k1", workspace_id="ws1", knowledge_base_id="kb1", title="Doc", content="content", owner_id="u1")
    defaults.update(overrides)
    return KnowledgeItem(**defaults)


# -- MemoryEntry lifecycle -----------------------------------------------------------

def test_memory_entry_defaults_active():
    entry = _entry()
    assert entry.status == MemoryStatus.ACTIVE
    assert entry.version == 1
    assert entry.access_count == 0


def test_archive_and_restore():
    entry = _entry()
    entry.archive()
    assert entry.status == MemoryStatus.ARCHIVED
    entry.restore()
    assert entry.status == MemoryStatus.ACTIVE


def test_restore_from_non_archived_raises():
    entry = _entry()
    with pytest.raises(InvalidTransitionError):
        entry.restore()


def test_expire_then_archive_allowed():
    entry = _entry()
    entry.expire()
    assert entry.status == MemoryStatus.EXPIRED
    entry.archive()
    assert entry.status == MemoryStatus.ARCHIVED


def test_supersede_records_pointer():
    entry = _entry()
    entry.supersede("m2")
    assert entry.status == MemoryStatus.SUPERSEDED
    assert entry.superseded_by_id == "m2"


def test_delete_is_terminal():
    entry = _entry()
    entry.delete()
    assert entry.is_terminal()
    with pytest.raises(InvalidTransitionError):
        entry.archive()


def test_deleted_cannot_transition_anywhere():
    entry = _entry()
    entry.delete()
    with pytest.raises(InvalidTransitionError):
        entry.expire()


def test_record_access_bumps_count_and_importance():
    entry = _entry(importance_score=0.5)
    entry.record_access(recency_boost=0.1)
    assert entry.access_count == 1
    assert entry.last_accessed_at is not None
    assert entry.importance_score == pytest.approx(0.6)


def test_record_access_importance_capped_at_one():
    entry = _entry(importance_score=0.98)
    entry.record_access(recency_boost=0.5)
    assert entry.importance_score == 1.0


def test_record_access_requires_active():
    entry = _entry()
    entry.archive()
    with pytest.raises(InvalidTransitionError):
        entry.record_access()


def test_update_content_bumps_version_and_clears_summary():
    entry = _entry()
    entry.summary = "old summary"
    entry.update_content("new content")
    assert entry.content == "new content"
    assert entry.version == 2
    assert entry.summary is None


def test_update_content_requires_active():
    entry = _entry()
    entry.archive()
    with pytest.raises(InvalidTransitionError):
        entry.update_content("x")


def test_summarize_sets_summary():
    entry = _entry()
    entry.summarize("a short summary")
    assert entry.summary == "a short summary"


def test_summarize_rejects_empty():
    entry = _entry()
    with pytest.raises(ValidationError):
        entry.summarize("   ")


def test_decayed_importance_without_decay_rate_is_unchanged():
    entry = _entry(importance_score=0.8)
    assert entry.decayed_importance(0.0) == 0.8


def test_decayed_importance_decreases_over_time():
    now = datetime.now(timezone.utc)
    entry = _entry(importance_score=0.8, last_accessed_at=now - timedelta(days=30))
    decayed = entry.decayed_importance(0.05, as_of=now)
    assert 0.0 <= decayed < 0.8


def test_decayed_importance_never_negative():
    now = datetime.now(timezone.utc)
    entry = _entry(importance_score=0.1, last_accessed_at=now - timedelta(days=3650))
    assert entry.decayed_importance(0.5, as_of=now) >= 0.0


def test_is_expired_false_without_expires_at():
    entry = _entry()
    assert entry.is_expired() is False


def test_is_expired_true_when_past_expiry():
    now = datetime.now(timezone.utc)
    entry = _entry(expires_at=now - timedelta(seconds=1))
    assert entry.is_expired(as_of=now) is True


def test_apply_retention_none_never_expires():
    entry = _entry()
    assert entry.apply_retention(None, created_at=datetime.now(timezone.utc) - timedelta(days=9999)) is False


def test_apply_retention_true_past_window():
    created = datetime.now(timezone.utc) - timedelta(days=400)
    entry = _entry()
    assert entry.apply_retention(365, created_at=created) is True


def test_apply_retention_false_within_window():
    created = datetime.now(timezone.utc) - timedelta(days=10)
    entry = _entry()
    assert entry.apply_retention(365, created_at=created) is False


# -- KnowledgeItem workflow -----------------------------------------------------------

def test_knowledge_item_defaults_draft():
    item = _item()
    assert item.status == KnowledgeItemStatus.DRAFT
    assert item.version == 1


def test_submit_review_approve_publish():
    item = _item()
    item.submit_for_review()
    assert item.status == KnowledgeItemStatus.IN_REVIEW
    item.approve_and_publish("reviewer1")
    assert item.status == KnowledgeItemStatus.PUBLISHED
    assert item.reviewed_by == "reviewer1"


def test_reject_returns_to_draft():
    item = _item()
    item.submit_for_review()
    item.reject("reviewer1")
    assert item.status == KnowledgeItemStatus.DRAFT
    assert item.reviewed_by == "reviewer1"


def test_publish_requires_in_review():
    item = _item()
    with pytest.raises(InvalidTransitionError):
        item.approve_and_publish("reviewer1")


def test_deprecate_then_archive():
    item = _item()
    item.submit_for_review()
    item.approve_and_publish("r1")
    item.deprecate()
    assert item.status == KnowledgeItemStatus.DEPRECATED
    item.archive()
    assert item.status == KnowledgeItemStatus.ARCHIVED


def test_archived_is_terminal():
    item = _item()
    item.archive()
    with pytest.raises(InvalidTransitionError):
        item.submit_for_review()


def test_new_version_bumps_and_updates_content():
    item = _item()
    v = item.new_version("revised content", summary="new summary")
    assert v == 2
    assert item.content == "revised content"
    assert item.summary == "new summary"


def test_new_version_rejected_when_archived():
    item = _item()
    item.archive()
    with pytest.raises(InvalidTransitionError):
        item.new_version("x")
