"""CollaborationAssetModel: a lightweight pointer this platform owns
for any object collaborated on (prompt, agent, workflow, knowledge
base, document, dataset, model, tool, dashboard, report, template,
project, or custom). The actual asset content lives in its owning
platform (Prompt Platform, Agent Platform, etc. — `external_ref_id`
is that platform's id for it); this platform only owns the
collaboration surface: comments, versions, reviews, activity,
sharing, and workspace/project/folder placement. That split keeps
this platform a genuine cross-cutting layer instead of a duplicate
copy of every other platform's data."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import AuditMixin, Base, IdMixin
from collaboration_platform.domain.enums import AssetStatus, AssetVisibility


class CollaborationAssetModel(IdMixin, AuditMixin, Base):
    __tablename__ = "cp_assets"
    __table_args__ = (
        UniqueConstraint("asset_type", "external_ref_id", name="uq_cp_asset_external_ref"),
        Index("ix_cp_assets_workspace", "workspace_id"),
        Index("ix_cp_assets_project", "project_id"),
        Index("ix_cp_assets_owner", "owner_id"),
    )

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("cp_projects.id"), nullable=True)
    folder_id: Mapped[str | None] = mapped_column(ForeignKey("cp_folders.id"), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    external_ref_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AssetStatus.ACTIVE.value, nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default=AssetVisibility.WORKSPACE.value, nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    asset_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
