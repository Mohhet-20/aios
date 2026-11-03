"""ORM models for the shared library surface: publishing an asset for
reuse across a workspace/organization/publicly, and per-user library
favorites (distinct from generic asset favorites — a library favorite
is "I want this reusable template in my quick-access list", scoped to
published library entries only)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow
from collaboration_platform.domain.enums import LibraryVisibility


class LibraryAssetModel(IdMixin, Base):
    __tablename__ = "cp_library_assets"
    __table_args__ = (UniqueConstraint("asset_id", name="uq_cp_library_asset"),)

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    library_type: Mapped[str] = mapped_column(String(30), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default=LibraryVisibility.PRIVATE.value, nullable=False)
    published_by: Mapped[str] = mapped_column(String(36), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    install_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unpublished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LibraryFavoriteModel(IdMixin, Base):
    __tablename__ = "cp_library_favorites"
    __table_args__ = (UniqueConstraint("user_id", "library_asset_id", name="uq_cp_library_favorite"),)

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    library_asset_id: Mapped[str] = mapped_column(ForeignKey("cp_library_assets.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
