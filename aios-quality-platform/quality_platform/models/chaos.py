"""Chaos Engineering Platform schema: one experiment row per failure
injection (guarded queued -> running -> completed/failed) across the
twelve failure types the prompt specifies, capped by a blast-radius
percentage, recording whether the target recovered and how long that
took."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class ChaosExperimentModel(IdMixin, AuditMixin, Base):
    __tablename__ = "qa_chaos_experiments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    failure_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    blast_radius_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recovered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    recovery_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
