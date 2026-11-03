"""ORM models for workspace/asset permissions, share links, external
sharing, the audit log, and retention policies. RBAC here is
deliberately a coarse per-workspace role (see `WorkspaceRole`) plus a
per-asset override, not a re-implementation of the Identity Platform's
fine-grained `resource_type:action` permission grammar — that engine
already exists one layer down; this platform only needs to answer
workspace/asset-level access questions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow
from collaboration_platform.domain.enums import PrincipalType, SharePermission, WorkspaceRole


class WorkspacePermissionModel(IdMixin, Base):
    __tablename__ = "cp_workspace_permissions"
    __table_args__ = (UniqueConstraint("workspace_id", "principal_type", "principal_id", name="uq_cp_workspace_permission"),)

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    principal_type: Mapped[str] = mapped_column(String(10), default=PrincipalType.USER.value, nullable=False)
    principal_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=WorkspaceRole.VIEWER.value, nullable=False)
    granted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AssetPermissionModel(IdMixin, Base):
    """A per-asset override on top of the workspace-level default — an
    asset owner can grant a narrower or wider role to a specific
    principal without changing their whole-workspace access."""
    __tablename__ = "cp_asset_permissions"
    __table_args__ = (UniqueConstraint("asset_id", "principal_type", "principal_id", name="uq_cp_asset_permission"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False, index=True)
    principal_type: Mapped[str] = mapped_column(String(10), default=PrincipalType.USER.value, nullable=False)
    principal_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=WorkspaceRole.VIEWER.value, nullable=False)
    granted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SharingLinkModel(IdMixin, Base):
    __tablename__ = "cp_sharing_links"
    __table_args__ = (Index("ix_cp_sharing_links_asset", "asset_id"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    permission: Mapped[str] = mapped_column(String(10), default=SharePermission.VIEW.value, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExternalShareModel(IdMixin, Base):
    __tablename__ = "cp_external_shares"
    __table_args__ = (Index("ix_cp_external_shares_asset", "asset_id"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    permission: Mapped[str] = mapped_column(String(10), default=SharePermission.VIEW.value, nullable=False)
    invited_by: Mapped[str] = mapped_column(String(36), nullable=False)
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLogEntryModel(IdMixin, Base):
    __tablename__ = "cp_audit_log"
    __table_args__ = (Index("ix_cp_audit_log_workspace", "workspace_id"), Index("ix_cp_audit_log_actor", "actor_id"))

    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    audit_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RetentionPolicyModel(IdMixin, Base):
    __tablename__ = "cp_retention_policies"
    __table_args__ = (UniqueConstraint("workspace_id", "resource_type", name="uq_cp_retention_policy"),)

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    retain_days: Mapped[int] = mapped_column(Integer, nullable=False)
    applies_to_deleted_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
