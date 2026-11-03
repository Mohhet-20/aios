from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class WorkspaceModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "workspaces"

    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="chart-1", nullable=False)


class ProjectModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "projects"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planning", nullable=False)
    progress: Mapped[int] = mapped_column(default=0, nullable=False)
