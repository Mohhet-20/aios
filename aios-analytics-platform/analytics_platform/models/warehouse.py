"""Data Warehouse & Metrics Registry schema: a metric catalog
(`MetricDefinitionModel`, one row per named metric a data source can
emit) plus an append-only fact table (`MetricEventModel`) that every
ingestion pipeline writes raw samples into. The aggregation engine
reads from `MetricEventModel` and writes rolled-up summaries into
`MetricRollupModel` (see `analytics.py`) — this file only owns raw
collection, not rollups."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class MetricDefinitionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "an_metric_definitions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    data_source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="count")
    aggregation_type: Mapped[str] = mapped_column(String(10), nullable=False, default="sum")
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class MetricEventModel(IdMixin, Base):
    __tablename__ = "an_metric_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    data_source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dimensions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
