"""ActivityEventModel: the single append-only event log every activity
feed (user/project/workspace/organization) reads from — one table,
filtered differently per feed, rather than separate per-scope tables
that could drift out of sync with each other."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow


class ActivityEventModel(IdMixin, Base):
    __tablename__ = "cp_activity_events"
    __table_args__ = (
        Index("ix_cp_activity_workspace", "workspace_id"),
        Index("ix_cp_activity_project", "project_id"),
        Index("ix_cp_activity_asset", "asset_id"),
        Index("ix_cp_activity_actor", "actor_id"),
        Index("ix_cp_activity_created", "created_at"),
    )

    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("cp_workspaces.id"), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("cp_projects.id"), nullable=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("cp_assets.id"), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
