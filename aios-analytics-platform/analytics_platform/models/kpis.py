"""KPI Engine schema: a KPI definition (target/thresholds, scoped
across the seven KPI scopes the prompt specifies) plus a snapshot
history table that records the KPI's computed value and health status
at each evaluation, giving KPI Manager UIs a real historical trend
line rather than only the current value."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class KpiDefinitionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "an_kpi_definitions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    higher_is_better: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    threshold_warning: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_critical: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)


class KpiSnapshotModel(IdMixin, Base):
    __tablename__ = "an_kpi_snapshots"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kpi_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    health: Mapped[str] = mapped_column(String(15), nullable=False, default="on_target")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
