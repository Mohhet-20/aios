"""Self-service export schema: one job row per export request (a
dashboard, report, or query result rendered to CSV/JSON/XLSX/PDF),
guarded queued -> running -> completed/failed."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class DataExportJobModel(IdMixin, AuditMixin, Base):
    __tablename__ = "an_export_jobs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    export_format: Mapped[str] = mapped_column(String(10), nullable=False, default="json")
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    output_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
