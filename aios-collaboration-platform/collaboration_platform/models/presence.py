"""ORM models for real-time collaboration: live presence/cursors,
editing sessions, and detected conflicts."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow
from collaboration_platform.domain.enums import PresenceStatus


class PresenceSessionModel(IdMixin, Base):
    __tablename__ = "cp_presence_sessions"
    __table_args__ = (Index("ix_cp_presence_asset", "asset_id"), Index("ix_cp_presence_user", "user_id"))

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    connection_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    cursor_position: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=PresenceStatus.ACTIVE.value, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EditSessionModel(IdMixin, Base):
    __tablename__ = "cp_edit_sessions"
    __table_args__ = (Index("ix_cp_edit_sessions_asset", "asset_id"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    base_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConflictRecordModel(IdMixin, Base):
    __tablename__ = "cp_conflict_records"
    __table_args__ = (Index("ix_cp_conflicts_asset", "asset_id"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    session_a_id: Mapped[str] = mapped_column(String(36), nullable=False)
    session_b_id: Mapped[str] = mapped_column(String(36), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolution_strategy: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
