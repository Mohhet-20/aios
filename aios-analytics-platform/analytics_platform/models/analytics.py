"""Aggregation Engine schema: one generic rollup table spanning all
four analytics domains the prompt specifies (business, ai, financial,
performance) and all four rollup periods (hourly, daily, weekly,
monthly), keyed by (metric_key, domain, period, period_start) — a
single table with a `domain`/`period` discriminator rather than
sixteen near-identical tables, the same generic-table-with-
discriminator precedent used for traffic rules in the API Gateway
Platform."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import Base, IdMixin, utcnow


class MetricRollupModel(IdMixin, Base):
    __tablename__ = "an_metric_rollups"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
