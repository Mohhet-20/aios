from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class OrganizationModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="starter", nullable=False)
    logo_initials: Mapped[str] = mapped_column(String(4), default="", nullable=False)


class OrganizationMembershipModel(IdMixin, AuditMixin, Base):
    __tablename__ = "organization_memberships"

    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)


class TeamModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "teams"

    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class TeamMembershipModel(IdMixin, AuditMixin, Base):
    __tablename__ = "team_memberships"

    team_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
