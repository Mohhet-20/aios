from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin


class MemoryItemModel(IdMixin, AuditMixin, Base):
    """Backs all three Memory Engine tiers (session/semantic/episodic) in
    one table, discriminated by `memory_type` — a pragmatic simplification
    versus three separate tables, since the shape (scope, content,
    relevance, embedding pointer) is identical across tiers and they're
    always queried the same way. `embedding_id` points into the vector
    store (`app.infrastructure.vector_store`) for semantic memory only."""

    __tablename__ = "memory_items"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
