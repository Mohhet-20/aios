"""EvaluationRunModel: one execution of an `EvaluationVersionModel`
against its bound dataset — the aggregate record (status, timing,
overall score). `EvaluationItemResultModel` is the per-dataset-item
detail (actual vs. expected output, per-metric scores, pass/fail) a run
fans out into; this split is what lets a dashboard show both "did this
evaluation pass overall" and "which specific inputs failed and why."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from eval_platform.database.base import Base, IdMixin, utcnow
from eval_platform.domain.enums import RunStatus


class EvaluationRunModel(Base, IdMixin):
    __tablename__ = "ep_evaluation_runs"

    evaluation_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_evaluations.id"), nullable=False, index=True)
    evaluation_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_evaluation_versions.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), default=RunStatus.PENDING.value, nullable=False, index=True)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    trigger_type: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)

    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Per-metric aggregate (avg/min/max) across every item")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)


class EvaluationItemResultModel(Base, IdMixin):
    __tablename__ = "ep_evaluation_item_results"

    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_evaluation_runs.id"), nullable=False, index=True)
    dataset_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ep_dataset_items.id"), nullable=True, index=True)

    input_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    expected_output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    actual_output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    metric_results: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{metric_key: score}")
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
