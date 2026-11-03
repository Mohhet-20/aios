"""ApprovalRequestModel: a human-in-the-loop gate tied to a paused
execution/node. `approval_chain` holds an ordered list of approver
groups for multi-step chains (e.g. [["manager-1"], ["finance-1",
"finance-2"]] — step 1 needs manager-1, step 2 needs any one of
finance-1/finance-2); `current_step` tracks progress through it.
`escalate_after` + `escalated_at` support time-based auto-escalation."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin, utcnow
from workflow_platform.domain.enums import ApprovalStatus


class ApprovalRequestModel(Base, IdMixin):
    __tablename__ = "wf_approval_requests"

    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_executions.id"), nullable=False, index=True)
    node_execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_node_executions.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING.value, nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    approval_chain: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="Ordered list of approver-id groups; each step needs any one approver from its group")
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity_level: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)

    decided_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    escalate_after: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    decided_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalCommentModel(Base, IdMixin):
    __tablename__ = "wf_approval_comments"

    approval_request_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_approval_requests.id"), nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
