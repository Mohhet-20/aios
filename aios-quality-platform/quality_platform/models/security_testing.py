"""Security Testing Engine schema: one scan row per security test run
(guarded queued -> running -> completed/failed) across the eleven
security test types the prompt specifies, plus individual findings
recorded against that scan."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class SecurityScanModel(IdMixin, AuditMixin, Base):
    __tablename__ = "qa_security_scans"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    security_test_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SecurityFindingModel(IdMixin, Base):
    __tablename__ = "qa_security_findings"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    security_scan_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
