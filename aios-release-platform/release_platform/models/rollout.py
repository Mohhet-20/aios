"""Rollout Engine schema: a rollout attached to a deployment, guarded
through its own planned -> in_progress -> paused/completed/aborted
lifecycle, across the 10 declared rollout strategies."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import AuditMixin, Base, IdMixin


class RolloutModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_rollouts"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    deployment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="planned", index=True)
    target_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_step_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
