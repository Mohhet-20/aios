"""Observability & Release Analytics schema: raw deployment metric
events (success rate inputs, rollback frequency, duration) and
periodic version-adoption snapshots."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import Base, IdMixin, utcnow


class DeploymentMetricModel(IdMixin, Base):
    __tablename__ = "rel_deployment_metrics"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    deployment_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metric_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReleaseAdoptionSnapshotModel(IdMixin, Base):
    __tablename__ = "rel_adoption_snapshots"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    adoption_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
