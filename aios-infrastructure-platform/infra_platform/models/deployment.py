"""Deployment strategies schema: a `DeploymentModel` guarded lifecycle
(pending -> in_progress -> succeeded/failed/rolled_back, with a
paused state for canary bake windows) covering rolling, blue-green,
canary, shadow, and recreate strategies via a `strategy` field rather
than five separate tables; traffic-split snapshots for canary/blue-
green; feature flags for gradual/targeted rollout; and an append-only
deployment event log (promotion/rollback/pause events) distinct from
the deployment's own current-state row."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class DeploymentModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_deployments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    service_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy: Mapped[str] = mapped_column(String(15), nullable=False, default="rolling")
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="pending", index=True)
    target_version: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    traffic_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrafficSplitModel(IdMixin, Base):
    __tablename__ = "infra_traffic_splits"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    deployment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    variant: Mapped[str] = mapped_column(String(20), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FeatureFlagModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_feature_flags"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class DeploymentEventModel(IdMixin, Base):
    __tablename__ = "infra_deployment_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    deployment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
