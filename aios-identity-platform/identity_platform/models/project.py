"""ProjectModel: the finest-grained scope in the org hierarchy —
organization -> workspace -> project — that roles/permissions can be
assigned against."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import AuditMixin, Base, IdMixin
from identity_platform.domain.enums import ProjectStatus


class ProjectModel(Base, IdMixin, AuditMixin):
    __tablename__ = "ip_projects"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ProjectStatus.ACTIVE.value, nullable=False, index=True)
