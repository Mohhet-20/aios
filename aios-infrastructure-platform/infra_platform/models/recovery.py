"""Disaster Recovery schema: backups (append-per-run, guarded status),
snapshots (point-in-time captures, optionally tied to a backup),
recovery plans (the reusable RPO/RTO-bearing definition), recovery
executions (a guarded run of a plan), and failover events (cross-
region failover attempts)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class BackupModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_backups"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="pending", index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    storage_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)


class SnapshotModel(IdMixin, Base):
    __tablename__ = "infra_snapshots"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    backup_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    storage_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RecoveryPlanModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_recovery_plans"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False)
    rpo_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    rto_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    target_region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RecoveryExecutionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_recovery_executions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    recovery_plan_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="initiated", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class FailoverEventModel(IdMixin, Base):
    __tablename__ = "infra_failover_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cluster_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    from_region: Mapped[str] = mapped_column(String(50), nullable=False)
    to_region: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="initiated", index=True)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
