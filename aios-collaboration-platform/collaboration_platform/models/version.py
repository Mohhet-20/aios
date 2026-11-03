"""ORM models for version control: immutable version snapshots,
branches, and merges."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow
from collaboration_platform.domain.enums import BranchStatus


class VersionModel(IdMixin, Base):
    __tablename__ = "cp_versions"
    __table_args__ = (
        UniqueConstraint("asset_id", "branch_name", "version_number", name="uq_cp_version_asset_branch_number"),
        Index("ix_cp_versions_asset", "asset_id"),
        Index("ix_cp_versions_parent", "parent_version_id"),
    )

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(ForeignKey("cp_versions.id"), nullable=True)
    content_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_release: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    release_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class BranchModel(IdMixin, Base):
    __tablename__ = "cp_branches"
    __table_args__ = (UniqueConstraint("asset_id", "name", name="uq_cp_branch_asset_name"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_version_id: Mapped[str | None] = mapped_column(ForeignKey("cp_versions.id"), nullable=True)
    head_version_id: Mapped[str | None] = mapped_column(ForeignKey("cp_versions.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=BranchStatus.OPEN.value, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MergeModel(IdMixin, Base):
    __tablename__ = "cp_merges"

    branch_id: Mapped[str] = mapped_column(ForeignKey("cp_branches.id"), nullable=False, index=True)
    target_branch_name: Mapped[str] = mapped_column(String(100), nullable=False)
    merged_version_id: Mapped[str | None] = mapped_column(ForeignKey("cp_versions.id"), nullable=True)
    strategy: Mapped[str] = mapped_column(String(20), nullable=False)
    conflict_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    merged_by: Mapped[str] = mapped_column(String(36), nullable=False)
    merged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
