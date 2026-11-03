"""Governance: append-only audit log + a generic ACL for prompt/workspace/
project resources."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from prompt_platform.database.base import Base, IdMixin, utcnow


class AuditLogEntryModel(Base, IdMixin):
    """Deliberately no AuditMixin/SoftDeleteMixin — this table IS the audit
    trail; it must never be edited or soft-deleted after the fact."""

    __tablename__ = "audit_log_entries"

    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PromptPermissionGrantModel(Base, IdMixin):
    __tablename__ = "prompt_permission_grants"

    principal_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_type: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False, doc="workspace|project|prompt")
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
