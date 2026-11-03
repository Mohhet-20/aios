"""Optimization runs and the suggestions they produce. A run may be
purely advisory (suggestions only) or may materialize a new draft
PromptVersion (result_version_id) when a suggestion is applied."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from prompt_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from prompt_platform.domain.enums import OptimizationObjective, RunStatus


class OptimizationRunModel(Base, IdMixin, AuditMixin):
    __tablename__ = "optimization_runs"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=False, index=True)
    objective: Mapped[str] = mapped_column(String(20), default=OptimizationObjective.QUALITY.value, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.PENDING.value, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(36), nullable=False)
    started_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    result_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("prompt_versions.id"), nullable=True,
        doc="Set when a suggestion from this run was applied, creating a new draft version.",
    )
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{suggestion_count, categories, token_delta, ...}")


class OptimizationSuggestionModel(Base, IdMixin):
    __tablename__ = "optimization_suggestions"

    optimization_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("optimization_runs.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True, doc="e.g. {token_delta: -120, est_cost_savings_pct: 18}")
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
