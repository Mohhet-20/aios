"""Threat detection findings — a guarded lifecycle record (detected ->
investigating -> confirmed/dismissed -> mitigated), one row per
detected incident-worthy signal (not every evaluated event, which
would belong in an append-only log the way guardrail evaluations do)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class ThreatDetectionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "sec_threat_detections"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    threat_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="detected", index=True)
    entity_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
