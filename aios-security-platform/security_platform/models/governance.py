"""AI governance schema. `GovernanceAssetModel` is a lightweight
pointer this platform owns for anything under governance (model,
prompt, workflow, dataset, agent, knowledge base) — same "own the
pointer, not the data" pattern as the Collaboration Platform's
`CollaborationAssetModel`. Approval requests/decisions mirror the
Collaboration Platform's review-workflow shape (a guarded
`ApprovalRequestModel` plus per-approver decision rows), since it's
the same underlying problem — a chain of reviewers must approve before
a lifecycle transition is allowed."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin, utcnow


class GovernanceAssetModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "sec_governance_assets"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    external_ref_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lifecycle_stage: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")


class ApprovalPolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "sec_approval_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approver_roles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class ApprovalRequestModel(IdMixin, AuditMixin, VersionedMixin, Base):
    __tablename__ = "sec_approval_requests"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requested_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_lifecycle_stage: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalDecisionModel(IdMixin, Base):
    __tablename__ = "sec_approval_decisions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    approver_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decision: Mapped[str] = mapped_column(String(10), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
