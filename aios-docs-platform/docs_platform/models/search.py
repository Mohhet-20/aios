"""Search Platform schema: a log of every query executed, powering
both the search experience (recent/popular queries) and analytics
(failed-search detection)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import IdMixin, Base, utcnow


class SearchQueryLogModel(IdMixin, Base):
    __tablename__ = "doc_search_query_logs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicked_doc_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
