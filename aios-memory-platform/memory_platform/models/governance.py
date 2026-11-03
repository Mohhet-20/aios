"""Governance: RBAC grants, retention policies, and the append-only audit
trail used by both memory lifecycle events and access/administrative
actions — one table serving both, the same consolidation the Agent
Platform used rather than modeling "memory audit" and "access audit" as
two redundant concepts."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from memory_platform.database.base import Base, IdMixin, utcnow


class PermissionGrantModel(Base, IdMixin):
    __tablename__ = "mem_permission_grants"

    principal_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_type: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False, doc="workspace|knowledge_base")
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RetentionPolicyModel(Base, IdMixin):
    __tablename__ = "mem_retention_policies"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    memory_type: Mapped[str | None] = mapped_column(String(40), nullable=True, doc="Null = applies to every memory type")
    scope_type: Mapped[str | None] = mapped_column(String(20), nullable=True, doc="Null = applies to every scope")
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    action_on_expiry: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AuditLogEntryModel(Base, IdMixin):
    """Deliberately no update/delete path — this IS the audit trail."""

    __tablename__ = "mem_audit_log_entries"

    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
