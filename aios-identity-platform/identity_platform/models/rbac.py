"""RBAC: `RoleModel` is a data-driven bundle of permission keys (a
built-in system role has `organization_id=None`; a custom role is
scoped to the organization that created it), `RoleAssignmentModel`
binds a principal (user/service_account/group) to a role at a specific
scope (system/organization/workspace/project) + `scope_id`, and
`PermissionModel` is the DB-facing catalog of every fine-grained
permission key — seeded from the in-code registry in
`authorization/registry.py`, mirroring the Evaluation Platform's
`MetricDefinitionModel` pattern (the actual enforcement logic lives in
code; this table is what a Role Manager UI queries without importing
Python)."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class RoleModel(Base, IdMixin, AuditMixin):
    __tablename__ = "ip_roles"

    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=True, index=True, doc="Null for a built-in system role available to every organization")
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permissions: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="List of permission keys this role grants")


class RoleAssignmentModel(Base, IdMixin):
    __tablename__ = "ip_role_assignments"

    principal_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_roles.id"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, doc="The organization/workspace/project id this grant applies to")
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PermissionModel(Base, IdMixin):
    __tablename__ = "ip_permissions"

    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


