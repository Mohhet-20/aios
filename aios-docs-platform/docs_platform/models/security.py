"""Security & Governance schema: RBAC role assignments (a user's
contributor role, optionally scoped to a specific doc space/page
rather than tenant-wide)."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import AuditMixin, Base, IdMixin


class RoleAssignmentModel(IdMixin, AuditMixin, Base):
    __tablename__ = "doc_role_assignments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    scope_ref: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
