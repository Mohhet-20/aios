"""EmbeddingRecordModel: our own durable metadata about a vector — the AI
Core's VectorStore holds the actual float array (in-memory today, a real
vector DB tomorrow) but never persists to our database, so anything we
need to survive a restart, audit, or query by (which model/version
produced it, which index it lives in, what it embeds) lives here instead.
"""
from __future__ import annotations

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from memory_platform.database.base import Base, IdMixin, utcnow


class EmbeddingRecordModel(Base, IdMixin):
    __tablename__ = "mem_embedding_records"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, doc="'memory_entry' | 'knowledge_item' | 'document_chunk' | 'kg_entity'")
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    vector_store_index: Mapped[str] = mapped_column(String(80), default="default", nullable=False, index=True, doc="Multi-index support — which logical index this vector lives in")

    model: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
