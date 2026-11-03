"""Prompt execution log — the observability record for every render+
execute call the platform makes (via testing, evaluation, experiments, or
a direct Studio "run" click)."""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from prompt_platform.database.base import Base, IdMixin, utcnow


class PromptExecutionLogModel(Base, IdMixin):
    __tablename__ = "prompt_execution_logs"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=False, index=True)
    environment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="studio", nullable=False, doc="studio|test|evaluation|experiment|deployment")

    model_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(60), nullable=True)

    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user_feedback_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
