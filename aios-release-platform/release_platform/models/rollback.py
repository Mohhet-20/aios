"""Rollback Engine schema: one row per rollback action taken against a
deployment, across the 8 declared rollback types (automatic, manual,
partial, database, configuration, feature, model, infrastructure)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import AuditMixin, Base, IdMixin


class RollbackModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_rollbacks"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    deployment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rollback_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    initiated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
