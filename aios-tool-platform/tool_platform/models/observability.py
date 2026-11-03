"""Structured execution log lines — the raw material `monitoring/observability_service.py` summarizes into timelines/metrics."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import Base, IdMixin, utcnow


class ExecutionLogModel(Base, IdMixin):
    __tablename__ = "tp_execution_logs"

    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_tool_executions.id"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(10), default="info", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    log_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
