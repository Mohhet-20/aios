"""Structured log ingestion table. Deliberately append-only (no
SoftDeleteMixin/AuditMixin.updated_at churn) — a log entry is never
edited, only ingested and, later, hard-deleted by the retention sweep."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import Base, IdMixin, utcnow


class LogEntryModel(IdMixin, Base):
    __tablename__ = "obs_log_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    component_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    level: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    span_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
