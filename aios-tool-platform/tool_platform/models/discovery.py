"""ToolFavoriteModel backs the "Favorites" surface in Tool Discovery.
"Recently Used" is deliberately NOT a separate table — it's derived by
querying `tp_tool_executions` ordered by `created_at` for a given
`triggered_by`, since the execution log already has that history and a
second copy of it would just be a cache invalidation problem waiting
to happen."""
from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import Base, IdMixin, utcnow


class ToolFavoriteModel(Base, IdMixin):
    __tablename__ = "tp_tool_favorites"

    tool_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_tools.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
