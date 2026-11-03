"""Security events (append-only, high-volume — every authentication,
authorization, policy/prompt/tool/workflow violation, secrets access,
risk change, threat detection, and administrative action) and the
immutable audit log (config/policy changes and security decisions —
narrower and longer-retained than the events feed, the same split the
Observability and Collaboration Platforms both draw between their
activity/event feed and their compliance-grade audit log)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.database.base import Base, IdMixin, utcnow


class SecurityEventModel(IdMixin, Base):
    __tablename__ = "sec_security_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="info")
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class AuditLogEntryModel(IdMixin, Base):
    __tablename__ = "sec_audit_log_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
