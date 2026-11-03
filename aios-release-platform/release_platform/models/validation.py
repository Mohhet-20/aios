"""Deployment Validation schema: one health-check run row per
(deployment, target) pair, across the 10 declared health-check
targets — application, API, database, workflow, AI services, agent
services, memory services, security platform, monitoring platform,
analytics platform."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import Base, IdMixin, utcnow


class HealthCheckRunModel(IdMixin, Base):
    __tablename__ = "rel_health_check_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    deployment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
