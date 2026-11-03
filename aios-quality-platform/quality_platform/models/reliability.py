"""Reliability Engineering schema: SLO definitions per service (a
target percentage over a rolling window, with a computed status) and
raw reliability metric snapshots (availability, reliability,
durability, error budget, MTTD, MTTR, MTBF, recovery success rate)
recorded over time."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class SloDefinitionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "qa_slo_definitions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    service_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    target_pct: Mapped[float] = mapped_column(Float, nullable=False, default=99.9)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="meeting", index=True)


class ReliabilityMetricSnapshotModel(IdMixin, Base):
    __tablename__ = "qa_reliability_snapshots"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    service_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
