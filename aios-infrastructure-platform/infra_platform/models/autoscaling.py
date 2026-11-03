"""Autoscaling schema: a generic `ScalingPolicyModel` (polymorphic
over `resource_type`/`resource_id`, the same pattern used by the
Security Platform's risk scores) covering horizontal, vertical,
cluster, GPU, queue-based, predictive, and cost-aware scaling, plus an
append-only scaling event log."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class ScalingPolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_scaling_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_type: Mapped[str] = mapped_column(String(15), nullable=False)
    min_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    target_metric: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ScalingEventModel(IdMixin, Base):
    __tablename__ = "infra_scaling_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    from_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    to_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
