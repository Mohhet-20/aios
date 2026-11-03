"""Observability schema for the quality platform itself: point-in-time
trend snapshots across the eight metric types the prompt specifies
(test executions, quality, regression, coverage, failure, performance,
reliability, release), giving every dashboard a real time series
rather than only the current value."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import Base, IdMixin, utcnow


class TrendSnapshotModel(IdMixin, Base):
    __tablename__ = "qa_trend_snapshots"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    subject_ref: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
