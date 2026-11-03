"""AuditLogEntryModel: a single consolidated audit table (not one per
domain) covering every governance-relevant action across this
platform — logins, permission/role changes, organization/workspace
events, API key issuance, security events, administrative actions."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import Base, IdMixin, utcnow


class AuditLogEntryModel(Base, IdMixin):
    __tablename__ = "ip_audit_log"

    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
