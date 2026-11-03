"""Time-series metrics. `MetricDefinitionModel` is metadata (registered
once per metric name); `MetricPointModel` is the actual time series,
one row per sample — append-only like logs."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class MetricDefinitionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "obs_metric_definitions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class MetricPointModel(IdMixin, Base):
    __tablename__ = "obs_metric_points"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    labels: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    component_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    service_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
