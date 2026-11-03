"""Observability, Analytics & Topology schema: raw time-series metric
points (one row per recorded sample — the nine metric types the
prompt specifies), a dependency graph edge table (service-to-service
call counts/latency, the raw material a topology view renders), and
periodic analytics snapshots (the eight report types the prompt
specifies) persisted per period rather than recomputed on every read."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import Base, IdMixin, utcnow


class GatewayMetricModel(IdMixin, Base):
    __tablename__ = "gw_metrics"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    route_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    service_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class DependencyEdgeModel(IdMixin, Base):
    __tablename__ = "gw_dependency_edges"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_service: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    to_service: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AnalyticsSnapshotModel(IdMixin, Base):
    __tablename__ = "gw_analytics_snapshots"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
