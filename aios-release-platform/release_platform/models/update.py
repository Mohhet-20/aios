"""Update Infrastructure schema: one row per update job applied to an
installation/environment, guarded through the shared job lifecycle,
across the 7 declared update types."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import AuditMixin, Base, IdMixin


class UpdateJobModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_update_jobs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    update_type: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    from_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
