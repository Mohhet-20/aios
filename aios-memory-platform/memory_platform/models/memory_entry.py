"""MemoryEntryModel: the unified, polymorphic record every one of the 16
memory types is stored as — `memory_type` + `scope_type`/`scope_id` are
the two orthogonal axes (what kind of memory, whose memory) rather than
16 separate tables. Conversation turns, episodic events, and procedural
steps all fit through `structured_content`; what makes each type behave
differently is its `MemoryTypePolicyModel` row plus, for the handful of
types with genuinely distinct interaction patterns, a thin service on
top (see `conversation_memory/`, `episodic_memory/`, `memory_core/`).
"""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from memory_platform.database.base import AuditMixin, Base, IdMixin
from memory_platform.domain.enums import MemoryStatus, SensitivityLevel


class MemoryEntryModel(Base, IdMixin, AuditMixin):
    __tablename__ = "mem_memory_entries"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("mem_workspaces.id"), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_content: Mapped[dict | None] = mapped_column(JSON, nullable=True, doc="Conversation-turn / episodic-event / procedural-step payload")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, doc="Compressed representation once summarized")

    embedding_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mem_embedding_records.id"), nullable=True)

    importance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    source: Mapped[str | None] = mapped_column(String(120), nullable=True, doc="e.g. an agent-execution id, a document id")
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True, doc="'agent_execution' | 'document' | 'user_input' | 'system'")
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=MemoryStatus.ACTIVE.value, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    superseded_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("mem_memory_entries.id"), nullable=True)

    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True, doc="Groups CONVERSATION-type turns")
    turn_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    occurred_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, doc="When an EPISODIC event happened, vs created_at = when recorded")
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    sensitivity_level: Mapped[str] = mapped_column(String(20), default=SensitivityLevel.INTERNAL.value, nullable=False)
