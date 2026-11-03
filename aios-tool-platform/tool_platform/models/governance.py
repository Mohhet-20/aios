"""RBAC grants + a single consolidated audit log — the same consolidation
(one table, not one per domain) the Memory/Agent/Workflow Platforms use."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import Base, IdMixin, utcnow
from tool_platform.domain.enums import ApprovalStatus


class PermissionGrantModel(Base, IdMixin):
    __tablename__ = "tp_permission_grants"

    principal_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_type: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalGateModel(Base, IdMixin):
    """A human-in-the-loop checkpoint for a HIGH/CRITICAL-sensitivity tool
    call — see `ToolSensitivity`'s docstring. One gate covers exactly one
    execution attempt: `consumed_at` is set the moment the Execution
    Engine actually spends the approval, so a gate can't be replayed
    across multiple calls even if it stays APPROVED in the database."""
    __tablename__ = "tp_approval_gates"

    resource_type: Mapped[str] = mapped_column(String(40), default="tool", nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity_level: Mapped[str] = mapped_column(String(20), default="high", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING.value, nullable=False, index=True)
    approver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLogEntryModel(Base, IdMixin):
    __tablename__ = "tp_audit_log"

    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
