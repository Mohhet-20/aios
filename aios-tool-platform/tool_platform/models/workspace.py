"""Workspace — the top of the resource hierarchy and isolation boundary
every tool, credential, execution, and schedule hangs off of."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import AuditMixin, Base, IdMixin


class WorkspaceModel(Base, IdMixin, AuditMixin):
    __tablename__ = "tp_workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
