"""Evaluation runs and their per-metric results."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from prompt_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from prompt_platform.domain.enums import EvalType, RunStatus


class EvaluationRunModel(Base, IdMixin, AuditMixin):
    __tablename__ = "evaluation_runs"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=False, index=True)
    compare_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=True, doc="Set for pairwise comparison runs")
    eval_type: Mapped[str] = mapped_column(String(20), default=EvalType.AUTOMATIC.value, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.PENDING.value, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(36), nullable=False)
    started_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{overall_score, metric_scores}")


class EvaluationResultModel(Base, IdMixin):
    __tablename__ = "evaluation_results"

    evaluation_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id"), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
