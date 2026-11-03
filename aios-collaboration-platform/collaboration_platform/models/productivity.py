"""ORM models for task assignments, checklists, bookmarks, and pinned
items — the personal/team productivity layer on top of assets."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow
from collaboration_platform.domain.enums import TaskStatus


class TaskModel(IdMixin, Base):
    __tablename__ = "cp_tasks"
    __table_args__ = (Index("ix_cp_tasks_workspace", "workspace_id"), Index("ix_cp_tasks_assignee", "assignee_id"))

    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("cp_projects.id"), nullable=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("cp_assets.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.TODO.value, nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChecklistModel(IdMixin, Base):
    __tablename__ = "cp_checklists"

    task_id: Mapped[str | None] = mapped_column(ForeignKey("cp_tasks.id"), nullable=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("cp_assets.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)


class ChecklistItemModel(IdMixin, Base):
    __tablename__ = "cp_checklist_items"
    __table_args__ = (Index("ix_cp_checklist_items_checklist", "checklist_id"),)

    checklist_id: Mapped[str] = mapped_column(ForeignKey("cp_checklists.id"), nullable=False)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class BookmarkModel(IdMixin, Base):
    __tablename__ = "cp_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "asset_id", name="uq_cp_bookmark"),)

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PinnedItemModel(IdMixin, Base):
    __tablename__ = "cp_pinned_items"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id", "asset_id", name="uq_cp_pinned_item"),)

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
