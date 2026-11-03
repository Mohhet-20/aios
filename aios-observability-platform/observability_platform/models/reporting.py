"""Generated reports. `result` holds the computed report payload as of
`generated_at` — a report is a point-in-time snapshot a caller can
re-fetch without recomputation, distinct from a dashboard (always
live) the same way a Collaboration Platform version snapshot is
distinct from a live document."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import Base, IdMixin, utcnow


class ReportModel(IdMixin, Base):
    __tablename__ = "obs_reports"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    generated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
