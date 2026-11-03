"""Capacity planning: snapshots are periodic point-in-time resource
usage samples (append-only); forecasts are a generated-on-demand
projection persisted so a caller can retrieve the same forecast later
without recomputing, stamped with the method used so it's honest about
being a simple trend projection, not a real ML forecast (see
`capacity/forecast_service.py`)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import Base, IdMixin, utcnow


class CapacitySnapshotModel(IdMixin, Base):
    __tablename__ = "obs_capacity_snapshots"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    component_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CapacityForecastModel(IdMixin, Base):
    __tablename__ = "obs_capacity_forecasts"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    component_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False, default="linear_trend")
    points: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    projected_exhaustion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
