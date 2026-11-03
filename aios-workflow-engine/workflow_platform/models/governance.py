"""Governance: RBAC grants and the single, consolidated, append-only
audit log — the same consolidation the Memory and Agent Platforms used
rather than modeling "workflow audit" and "execution audit" as separate,
redundant concepts."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin, utcnow


class PermissionGrantModel(Base, IdMixin):
    __tablename__ = "wf_permission_grants"

    principal_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_type: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False, doc="workspace | workflow")
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLogEntryModel(Base, IdMixin):
    """Deliberately no update/delete path — this IS the audit trail."""

    __tablename__ = "wf_audit_log_entries"

    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
