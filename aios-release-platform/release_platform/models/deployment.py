"""Deployment Orchestration schema: one row per deployment attempt,
guarded through the shared queued -> in_progress -> succeeded/failed/
rolled_back job lifecycle, targeting one of the 9 declared deployment
target types."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import AuditMixin, Base, IdMixin


class DeploymentModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_deployments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    release_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    environment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    initiated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
