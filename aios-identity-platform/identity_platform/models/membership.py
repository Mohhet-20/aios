"""One membership model per scope (organization/workspace/team/
project/group) rather than one polymorphic table — each scope has its
own natural uniqueness constraint (a user is a member of a given
organization at most once) and its own set of status transitions,
so keeping them separate avoids a nullable-everything table with
different meaning per row."""
from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import Base, IdMixin, utcnow
from identity_platform.domain.enums import MembershipStatus


class OrganizationMembershipModel(Base, IdMixin):
    __tablename__ = "ip_organization_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_membership"),)

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=MembershipStatus.ACTIVE.value, nullable=False, index=True)
    invited_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    joined_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    removed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkspaceMembershipModel(Base, IdMixin):
    __tablename__ = "ip_workspace_memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),)

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_workspaces.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=MembershipStatus.ACTIVE.value, nullable=False, index=True)
    joined_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    removed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TeamMembershipModel(Base, IdMixin):
    __tablename__ = "ip_team_memberships"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_membership"),)

    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_teams.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    joined_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProjectMembershipModel(Base, IdMixin):
    __tablename__ = "ip_project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_membership"),)

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_projects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    joined_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class GroupMembershipModel(Base, IdMixin):
    __tablename__ = "ip_group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_membership"),)

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_groups.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    joined_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
