"""Retrieval and context-assembly logs — every query and every prompt
assembly logs one row here, the same "one shared choke point" pattern
the Prompt Platform used for its own observability, so latency/quality
rollups don't need every caller to reimplement logging."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from memory_platform.database.base import Base, IdMixin, utcnow


class RetrievalLogModel(Base, IdMixin):
    __tablename__ = "mem_retrieval_logs"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    search_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_filters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ContextAssemblyLogModel(Base, IdMixin):
    __tablename__ = "mem_context_assembly_logs"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_used: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    compression_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
