"""WorkspaceModel: an isolation/organization sub-boundary inside one
organization — every workspace-scoped resource (teams, projects, and
every AIOS platform's own workspace-scoped data) hangs off this id."""
from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin
from identity_platform.domain.enums import WorkspaceStatus


class WorkspaceModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "ip_workspaces"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=WorkspaceStatus.ACTIVE.value, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
