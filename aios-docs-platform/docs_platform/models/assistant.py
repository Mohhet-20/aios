"""AI Documentation Assistant schema: one row per question asked,
recording the retrieved related documents, the generated answer, and
a confidence score — the raw material `AssistantService` and the
observability layer both read from."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import IdMixin, Base, utcnow


class AssistantSessionModel(IdMixin, Base):
    __tablename__ = "doc_assistant_sessions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_doc_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
