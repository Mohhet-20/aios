"""Collaboration schema: comments, review requests (guarded pending ->
approved/changes_requested/rejected — status is a simple field guarded
directly in-service, per this platform's domain-layer docstring), and
an append-only audit trail."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import Base, IdMixin, utcnow


class CommentModel(IdMixin, Base):
    __tablename__ = "doc_comments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class ReviewModel(IdMixin, Base):
    __tablename__ = "doc_reviews"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLogEntryModel(IdMixin, Base):
    __tablename__ = "doc_audit_log_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
