"""Infra observability schema: a generic time-series metric point
(infrastructure/deployment/inference/training metrics all share this
shape, distinguished by `metric_name`/`resource_type`/`tags`) and
cluster health check results."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import Base, IdMixin, utcnow


class InfraMetricModel(IdMixin, Base):
    __tablename__ = "infra_metrics"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class ClusterHealthCheckModel(IdMixin, Base):
    __tablename__ = "infra_cluster_health_checks"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
