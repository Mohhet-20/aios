"""Top-level org/workspace container every agent, task, and permission
grant is scoped to — same pattern as the Prompt Platform."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import AuditMixin, Base, IdMixin


class WorkspaceModel(Base, IdMixin, AuditMixin):
    __tablename__ = "agent_workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
