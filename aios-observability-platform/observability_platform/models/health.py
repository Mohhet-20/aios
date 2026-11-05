"""Health monitoring. `HealthCheckResultModel` is an append-only time
series (one row per check run); current status is deliberately NOT a
cached column anywhere — it's always derived from the latest result per
component, the same anti-drift discipline every other AIOS platform's
observability layer follows."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import Base, IdMixin, utcnow


class HealthCheckResultModel(IdMixin, Base):
    __tablename__ = "obs_health_check_results"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    component_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
