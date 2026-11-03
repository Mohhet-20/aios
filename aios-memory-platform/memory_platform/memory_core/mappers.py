"""ORM <-> domain-entity mapping for MemoryEntryModel/MemoryEntry — kept
in one place so the lifecycle service never hand-rolls field copying."""
from __future__ import annotations

from memory_platform.domain.entities import MemoryEntry
from memory_platform.domain.enums import MemoryStatus
from memory_platform.models.memory_entry import MemoryEntryModel


def to_domain(model: MemoryEntryModel) -> MemoryEntry:
    return MemoryEntry(
        id=model.id,
        workspace_id=model.workspace_id,
        memory_type=model.memory_type,
        scope_type=model.scope_type,
        scope_id=model.scope_id,
        content=model.content,
        title=model.title,
        structured_content=model.structured_content,
        summary=model.summary,
        importance_score=model.importance_score,
        confidence=model.confidence,
        source=model.source,
        source_type=model.source_type,
        tags=list(model.tags or []),
        status=MemoryStatus(model.status),
        version=model.version,
        superseded_by_id=model.superseded_by_id,
        conversation_id=model.conversation_id,
        turn_index=model.turn_index,
        occurred_at=model.occurred_at,
        expires_at=model.expires_at,
        last_accessed_at=model.last_accessed_at,
        access_count=model.access_count,
        sensitivity_level=model.sensitivity_level,
    )


def apply_to_model(entity: MemoryEntry, model: MemoryEntryModel) -> MemoryEntryModel:
    model.content = entity.content
    model.title = entity.title
    model.structured_content = entity.structured_content
    model.summary = entity.summary
    model.importance_score = entity.importance_score
    model.confidence = entity.confidence
    model.tags = list(entity.tags or [])
    model.status = entity.status.value
    model.version = entity.version
    model.superseded_by_id = entity.superseded_by_id
    model.expires_at = entity.expires_at
    model.last_accessed_at = entity.last_accessed_at
    model.access_count = entity.access_count
    return model
