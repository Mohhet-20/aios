"""Documentation Analytics schema: raw usage events across the five
types the prompt specifies (page views, search queries, tutorial
completions, feedback, broken links), separate feedback-score records,
and broken-link tracking with a resolved flag."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import Base, IdMixin, utcnow


class AnalyticsEventModel(IdMixin, Base):
    __tablename__ = "doc_analytics_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    subject_ref: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class FeedbackModel(IdMixin, Base):
    __tablename__ = "doc_feedback"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class BrokenLinkModel(IdMixin, Base):
    __tablename__ = "doc_broken_links"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
