"""Knowledge Graph interfaces: entities (documents/projects/users/agents/
workflows/concepts/topics/knowledge-items/memory-entries, or anything else
via entity_type='custom') and typed relationships between them. This is a
real, queryable graph substrate backed by two tables — the documented
seam for a future dedicated graph database (Neo4j etc.) to replace
without `KnowledgeGraphService`'s callers changing."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from memory_platform.database.base import Base, IdMixin, utcnow


class KGEntityModel(Base, IdMixin):
    __tablename__ = "mem_kg_entities"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_workspaces.id"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True, doc="Points at the underlying row (document/knowledge_item/memory_entry/...) this entity mirrors, if any")
    entity_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mem_embedding_records.id"), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class KGRelationshipModel(Base, IdMixin):
    __tablename__ = "mem_kg_relationships"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_workspaces.id"), nullable=False, index=True)
    source_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_kg_entities.id"), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_kg_entities.id"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True, doc="Free-text — see domain.enums.WellKnownRelationType for the documented vocabulary")
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    relationship_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
