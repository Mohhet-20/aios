"""TeamModel: a membership grouping either org-wide or scoped to one
workspace — distinct from `GroupModel`, which is a lighter-weight
permission-bundling construct with no workspace/project hierarchy of
its own."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import AuditMixin, Base, IdMixin
from identity_platform.domain.enums import TeamStatus


class TeamModel(Base, IdMixin, AuditMixin):
    __tablename__ = "ip_teams"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ip_workspaces.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TeamStatus.ACTIVE.value, nullable=False, index=True)
