"""Real-time cost intelligence: individual cost records (append-only
ledger), per-entity budgets, and threshold-crossing alerts."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from perf_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class CostRecordModel(IdMixin, AuditMixin, Base):
    __tablename__ = "perf_cost_records"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    unit_count: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class BudgetModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "perf_budgets"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(16), nullable=False, default="monthly")
    limit_usd: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CostAlertModel(IdMixin, AuditMixin, Base):
    __tablename__ = "perf_cost_alerts"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    budget_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    threshold_pct: Mapped[float] = mapped_column(Float, nullable=False)
    spend_usd: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
