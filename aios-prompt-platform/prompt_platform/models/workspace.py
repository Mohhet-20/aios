"""Prompt Workspaces and Projects — lightweight organizational containers
scoped to this platform. Identity (users/organizations) is owned by the
AIOS backend (Phase 3); this platform stores opaque owner/organization
IDs rather than re-implementing user management, so `organization_id`/
`owner_id` here are just indexed strings, not foreign keys into a local
users table.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from prompt_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class PromptWorkspaceModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "prompt_workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    projects: Mapped[list[PromptProjectModel]] = relationship(back_populates="workspace")


class PromptProjectModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "prompt_projects"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    workspace: Mapped[PromptWorkspaceModel] = relationship(back_populates="projects")
