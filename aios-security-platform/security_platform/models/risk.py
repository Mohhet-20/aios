"""Risk scores are append-only time series, exactly like the
Observability Platform's health-check results — an entity's "current"
risk is always derived from its latest score, never cached, so it can
never silently go stale."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.database.base import Base, IdMixin, utcnow


class RiskScoreModel(IdMixin, Base):
    __tablename__ = "sec_risk_scores"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    factors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
