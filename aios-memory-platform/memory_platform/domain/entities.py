"""Pure-Python domain aggregates — no ORM/SQLAlchemy imports here, same
separation every prior AIOS project used. `MemoryEntry` owns the memory
lifecycle state machine (creation/retrieval/update/versioning/expiration/
archiving/summarization/importance-scoring/conflict-resolution/deletion);
`KnowledgeItem` owns the knowledge review/publish workflow.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from memory_platform.core.exceptions import InvalidTransitionError, ValidationError
from memory_platform.core.time_utils import as_aware_utc
from memory_platform.domain.enums import KnowledgeItemStatus, MemoryStatus
from memory_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


# -- MemoryEntry ------------------------------------------------------------------

_MEMORY_STATUS_TRANSITIONS: dict[MemoryStatus, set[MemoryStatus]] = {
    MemoryStatus.ACTIVE: {MemoryStatus.ARCHIVED, MemoryStatus.EXPIRED, MemoryStatus.SUPERSEDED, MemoryStatus.DELETED},
    MemoryStatus.ARCHIVED: {MemoryStatus.ACTIVE, MemoryStatus.DELETED},
    MemoryStatus.EXPIRED: {MemoryStatus.ARCHIVED, MemoryStatus.DELETED},
    MemoryStatus.SUPERSEDED: {MemoryStatus.DELETED},
    MemoryStatus.DELETED: set(),
}


@dataclass
class MemoryEntry:
    id: str
    workspace_id: str
    memory_type: str
    scope_type: str
    scope_id: str
    content: str
    title: str | None = None
    structured_content: dict | None = None
    summary: str | None = None
    importance_score: float = 0.5
    confidence: float | None = None
    source: str | None = None
    source_type: str | None = None
    tags: list = field(default_factory=list)
    status: MemoryStatus = MemoryStatus.ACTIVE
    version: int = 1
    superseded_by_id: str | None = None
    conversation_id: str | None = None
    turn_index: int | None = None
    occurred_at: datetime | None = None
    expires_at: datetime | None = None
    last_accessed_at: datetime | None = None
    access_count: int = 0
    sensitivity_level: str = "internal"

    def _transition(self, target: MemoryStatus) -> None:
        allowed = _MEMORY_STATUS_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"MemoryEntry '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def is_terminal(self) -> bool:
        return self.status == MemoryStatus.DELETED

    # -- retrieval / access tracking -------------------------------------------

    def record_access(self, *, recency_boost: float = 0.05) -> None:
        """Every retrieval bumps access_count and last_accessed_at, and
        gives importance a small boost — a memory that keeps getting
        retrieved is more likely to matter than one nobody's touched."""
        if self.status != MemoryStatus.ACTIVE:
            raise InvalidTransitionError(f"MemoryEntry '{self.id}' is not ACTIVE (status: {self.status.value}) and cannot be accessed")
        self.access_count += 1
        self.last_accessed_at = _now()
        self.importance_score = min(1.0, self.importance_score + recency_boost)

    # -- update / versioning ----------------------------------------------------

    def update_content(self, content: str, *, structured_content: dict | None = None) -> None:
        if self.status != MemoryStatus.ACTIVE:
            raise InvalidTransitionError(f"MemoryEntry '{self.id}' is not ACTIVE (status: {self.status.value}) and cannot be updated")
        self.content = content
        if structured_content is not None:
            self.structured_content = structured_content
        self.summary = None  # a content change invalidates any prior compressed summary
        self.version += 1

    def summarize(self, summary_text: str) -> None:
        if not summary_text.strip():
            raise ValidationError("summary text must not be empty")
        self.summary = summary_text

    # -- lifecycle ----------------------------------------------------------------

    def archive(self) -> None:
        self._transition(MemoryStatus.ARCHIVED)

    def restore(self) -> None:
        if self.status != MemoryStatus.ARCHIVED:
            raise InvalidTransitionError(f"MemoryEntry '{self.id}' can only be restored from ARCHIVED (status: {self.status.value})")
        self._transition(MemoryStatus.ACTIVE)

    def expire(self) -> None:
        self._transition(MemoryStatus.EXPIRED)

    def supersede(self, new_entry_id: str) -> None:
        """Conflict resolution: this entry is superseded by a newer one —
        recorded, not deleted, so the prior value stays inspectable."""
        self._transition(MemoryStatus.SUPERSEDED)
        self.superseded_by_id = new_entry_id

    def delete(self) -> None:
        self._transition(MemoryStatus.DELETED)

    # -- importance decay / retention ---------------------------------------------

    def decayed_importance(self, decay_rate: float, *, as_of: datetime | None = None) -> float:
        """Exponential decay from the last-accessed (or created) timestamp
        — bounded to [0, 1], never goes negative the way a naive linear
        subtraction would given enough elapsed time."""
        if decay_rate <= 0:
            return self.importance_score
        as_of = as_of or _now()
        anchor = as_aware_utc(self.last_accessed_at) if self.last_accessed_at is not None else as_of
        days_elapsed = max(0.0, (as_of - anchor).total_seconds() / 86400.0)
        return max(0.0, min(1.0, self.importance_score * math.exp(-decay_rate * days_elapsed)))

    def is_expired(self, *, as_of: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (as_of or _now()) >= as_aware_utc(self.expires_at)

    def apply_retention(self, retention_days: int | None, *, created_at: datetime, as_of: datetime | None = None) -> bool:
        """Returns True if this entry should be considered expired under a
        `retention_days` policy, given when it was created — does not
        mutate state, just answers the question the lifecycle service acts on."""
        if retention_days is None:
            return False
        as_of = as_of or _now()
        return as_of >= as_aware_utc(created_at) + timedelta(days=retention_days)


# -- KnowledgeItem ------------------------------------------------------------------

_KNOWLEDGE_STATUS_TRANSITIONS: dict[KnowledgeItemStatus, set[KnowledgeItemStatus]] = {
    KnowledgeItemStatus.DRAFT: {KnowledgeItemStatus.IN_REVIEW, KnowledgeItemStatus.ARCHIVED},
    KnowledgeItemStatus.IN_REVIEW: {KnowledgeItemStatus.PUBLISHED, KnowledgeItemStatus.DRAFT, KnowledgeItemStatus.ARCHIVED},
    KnowledgeItemStatus.PUBLISHED: {KnowledgeItemStatus.DEPRECATED, KnowledgeItemStatus.ARCHIVED},
    KnowledgeItemStatus.DEPRECATED: {KnowledgeItemStatus.ARCHIVED},
    KnowledgeItemStatus.ARCHIVED: set(),
}


@dataclass
class KnowledgeItem:
    id: str
    workspace_id: str
    knowledge_base_id: str
    title: str
    content: str
    owner_id: str
    collection_id: str | None = None
    summary: str | None = None
    category: str | None = None
    tags: list = field(default_factory=list)
    status: KnowledgeItemStatus = KnowledgeItemStatus.DRAFT
    version: int = 1
    reviewed_by: str | None = None

    def _transition(self, target: KnowledgeItemStatus) -> None:
        allowed = _KNOWLEDGE_STATUS_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"KnowledgeItem '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def submit_for_review(self) -> None:
        self._transition(KnowledgeItemStatus.IN_REVIEW)

    def approve_and_publish(self, reviewed_by: str) -> None:
        if self.status != KnowledgeItemStatus.IN_REVIEW:
            raise InvalidTransitionError(f"KnowledgeItem '{self.id}' must be IN_REVIEW to publish (status: {self.status.value})")
        self.reviewed_by = reviewed_by
        self._transition(KnowledgeItemStatus.PUBLISHED)

    def reject(self, reviewed_by: str) -> None:
        if self.status != KnowledgeItemStatus.IN_REVIEW:
            raise InvalidTransitionError(f"KnowledgeItem '{self.id}' must be IN_REVIEW to reject (status: {self.status.value})")
        self.reviewed_by = reviewed_by
        self._transition(KnowledgeItemStatus.DRAFT)

    def deprecate(self) -> None:
        self._transition(KnowledgeItemStatus.DEPRECATED)

    def archive(self) -> None:
        self._transition(KnowledgeItemStatus.ARCHIVED)

    def new_version(self, content: str, *, summary: str | None = None) -> int:
        if self.status == KnowledgeItemStatus.ARCHIVED:
            raise InvalidTransitionError(f"KnowledgeItem '{self.id}' is ARCHIVED and cannot be revised")
        self.content = content
        if summary is not None:
            self.summary = summary
        self.version += 1
        return self.version
