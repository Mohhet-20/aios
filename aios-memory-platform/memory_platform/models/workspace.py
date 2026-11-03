"""Top-level org/workspace container every memory entry, knowledge base,
and document is scoped to — the isolation boundary the security model is
built on."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from memory_platform.database.base import AuditMixin, Base, IdMixin


class WorkspaceModel(Base, IdMixin, AuditMixin):
    __tablename__ = "mem_workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
