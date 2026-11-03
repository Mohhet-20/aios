"""Observability schema for the analytics platform itself: dashboard/
report/query/visualization usage events, forecast accuracy tracking
(predicted vs. actual, once the forecast horizon has passed), and
recommendation-outcome tracking (accepted/dismissed/implemented) so
the platform can measure whether its own suggestions are useful."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import Base, IdMixin, utcnow


class UsageEventModel(IdMixin, Base):
    __tablename__ = "an_usage_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class QueryPerformanceModel(IdMixin, Base):
    __tablename__ = "an_query_performance"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    query_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class ForecastAccuracyModel(IdMixin, Base):
    __tablename__ = "an_forecast_accuracy"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    forecast_job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RecommendationOutcomeModel(IdMixin, Base):
    __tablename__ = "an_recommendation_outcomes"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(15), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
