"""ORM models for saved searches and per-user recent items (an
explicit LRU-style table rather than deriving "recent" from the
activity feed, since recency here means *viewed*, not just changed)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow


class SavedSearchModel(IdMixin, Base):
    __tablename__ = "cp_saved_searches"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    query: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RecentItemModel(IdMixin, Base):
    __tablename__ = "cp_recent_items"
    __table_args__ = (UniqueConstraint("user_id", "asset_id", name="uq_cp_recent_item"), Index("ix_cp_recent_items_user", "user_id"))

    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
