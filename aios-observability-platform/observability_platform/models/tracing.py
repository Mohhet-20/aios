"""Distributed tracing: one `TraceModel` row summarizing a whole trace
(denormalized root service/duration/span_count for fast trace-list
queries) plus many `SpanModel` rows, each pointing at its trace by the
trace's own `trace_id` string (not the row's `id`) so ingestion doesn't
need a lookup — spans typically arrive from many services concurrently,
often before the trace summary row itself is finalized."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import Base, IdMixin, utcnow


class TraceModel(IdMixin, Base):
    __tablename__ = "obs_traces"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    root_service: Mapped[str | None] = mapped_column(String(200), nullable=True)
    root_operation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="unset")
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    span_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class SpanModel(IdMixin, Base):
    __tablename__ = "obs_spans"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    span_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    service_name: Mapped[str] = mapped_column(String(200), nullable=False)
    operation_name: Mapped[str] = mapped_column(String(200), nullable=False)
    span_kind: Mapped[str] = mapped_column(String(30), nullable=False, default="internal")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="unset")
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
