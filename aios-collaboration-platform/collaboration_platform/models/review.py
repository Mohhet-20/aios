"""ORM models for review requests, reviewer assignments (sequential or
parallel chains), and workspace-level policy-based approval rules."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow
from collaboration_platform.domain.enums import ReviewAssignmentStatus, ReviewStatus


class ApprovalPolicyModel(IdMixin, Base):
    __tablename__ = "cp_approval_policies"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    asset_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    required_approvals: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sequential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_approve_rules: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReviewRequestModel(IdMixin, Base):
    __tablename__ = "cp_review_requests"
    __table_args__ = (Index("ix_cp_review_requests_asset", "asset_id"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    version_id: Mapped[str | None] = mapped_column(ForeignKey("cp_versions.id"), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("cp_approval_policies.id"), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ReviewStatus.PENDING.value, nullable=False)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_approvals: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewAssignmentModel(IdMixin, Base):
    __tablename__ = "cp_review_assignments"
    __table_args__ = (Index("ix_cp_review_assignments_request", "review_request_id"), Index("ix_cp_review_assignments_reviewer", "reviewer_id"))

    review_request_id: Mapped[str] = mapped_column(ForeignKey("cp_review_requests.id"), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ReviewAssignmentStatus.PENDING.value, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
