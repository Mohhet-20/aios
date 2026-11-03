"""GroupModel: a lightweight, org-scoped principal used purely for
bundling permission grants (`RoleAssignmentModel.principal_type ==
"group"`) — unlike a Team, a group has no workspace hierarchy and
exists only to make "grant this role to these 40 people at once"
practical."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import AuditMixin, Base, IdMixin


class GroupModel(Base, IdMixin, AuditMixin):
    __tablename__ = "ip_groups"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
