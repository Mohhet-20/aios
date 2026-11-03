"""Governance: approval gates for sensitive/autonomous tasks, the
append-only audit log, and RBAC permission grants — same pattern as the
Prompt Platform, scoped to agents/tasks/tool calls instead of prompts."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import Base, IdMixin, utcnow
from agent_platform.domain.enums import ApprovalStatus


class ApprovalGateModel(Base, IdMixin):
    __tablename__ = "agent_approval_gates"

    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=False, index=True)
    requested_by_agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    approver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING.value, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    sensitivity_level: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    requested_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLogEntryModel(Base, IdMixin):
    """Deliberately no AuditMixin/SoftDeleteMixin — this IS the audit
    trail; it must never be edited or soft-deleted after the fact."""

    __tablename__ = "agent_audit_log_entries"

    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PermissionGrantModel(Base, IdMixin):
    __tablename__ = "agent_permission_grants"

    principal_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_type: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False, doc="workspace|agent")
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
