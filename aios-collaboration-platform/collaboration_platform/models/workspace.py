"""ORM models for workspaces, projects, folders, collections, tags, and
favorites — the containment/organization layer everything else in this
platform hangs off of."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from collaboration_platform.domain.enums import ProjectStatus, WorkspaceStatus, WorkspaceType


class WorkspaceTemplateModel(IdMixin, AuditMixin, Base):
    __tablename__ = "cp_workspace_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(default=False, nullable=False)


class WorkspaceModel(IdMixin, AuditMixin, Base):
    __tablename__ = "cp_workspaces"
    __table_args__ = (Index("ix_cp_workspaces_org", "organization_id"),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    workspace_type: Mapped[str] = mapped_column(String(20), default=WorkspaceType.TEAM.value, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=WorkspaceStatus.ACTIVE.value, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("cp_workspace_templates.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    workspace_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkspaceMemberModel(IdMixin, AuditMixin, Base):
    __tablename__ = "cp_workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_cp_workspace_member"),)

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    invited_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ProjectModel(IdMixin, AuditMixin, Base):
    __tablename__ = "cp_projects"
    __table_args__ = (Index("ix_cp_projects_workspace", "workspace_id"),)

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ProjectStatus.ACTIVE.value, nullable=False)
    project_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class FolderModel(IdMixin, AuditMixin, Base):
    __tablename__ = "cp_folders"
    __table_args__ = (Index("ix_cp_folders_workspace", "workspace_id"), Index("ix_cp_folders_parent", "parent_folder_id"))

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("cp_projects.id"), nullable=True)
    parent_folder_id: Mapped[str | None] = mapped_column(ForeignKey("cp_folders.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class CollectionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "cp_collections"
    __table_args__ = (Index("ix_cp_collections_workspace", "workspace_id"),)

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False)


class CollectionItemModel(IdMixin, Base):
    __tablename__ = "cp_collection_items"
    __table_args__ = (UniqueConstraint("collection_id", "asset_id", name="uq_cp_collection_item"),)

    collection_id: Mapped[str] = mapped_column(ForeignKey("cp_collections.id"), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False, index=True)
    added_by: Mapped[str] = mapped_column(String(36), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TagModel(IdMixin, AuditMixin, Base):
    __tablename__ = "cp_tags"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_cp_tag_workspace_name"),)

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)


class AssetTagModel(IdMixin, Base):
    __tablename__ = "cp_asset_tags"
    __table_args__ = (UniqueConstraint("asset_id", "tag_id", name="uq_cp_asset_tag"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False, index=True)
    tag_id: Mapped[str] = mapped_column(ForeignKey("cp_tags.id"), nullable=False, index=True)


class FavoriteModel(IdMixin, Base):
    __tablename__ = "cp_favorites"
    __table_args__ = (UniqueConstraint("user_id", "asset_id", name="uq_cp_favorite_user_asset"),)

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
