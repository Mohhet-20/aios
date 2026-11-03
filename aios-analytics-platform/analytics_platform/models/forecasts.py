"""Forecasting Engine schema: one job row per forecast run, guarded
queued -> running -> completed/failed, storing both the method used
and the resulting prediction series so a caller can see exactly how a
number was produced, not just the number itself."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class ForecastJobModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "an_forecast_jobs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    forecast_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(25), nullable=False, default="moving_average")
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
