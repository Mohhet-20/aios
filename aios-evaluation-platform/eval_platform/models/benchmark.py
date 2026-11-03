"""BenchmarkModel: a reusable comparison setup (model benchmarking,
prompt A/B/multivariate testing, agent or workflow comparison) bound to
a dataset. `BenchmarkRunModel` is one execution of that comparison
across a set of named candidates; `BenchmarkCandidateResultModel` is
one candidate's aggregate result within that run — what a Model
Comparison or Prompt Comparison dashboard renders as columns."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from eval_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow
from eval_platform.domain.enums import RunStatus


class BenchmarkModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "ep_benchmarks"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_workspaces.id"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    benchmark_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ep_datasets.id"), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    metric_keys: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class BenchmarkRunModel(Base, IdMixin):
    __tablename__ = "ep_benchmark_runs"

    benchmark_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_benchmarks.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.PENDING.value, nullable=False, index=True)
    candidates: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc='[{"label": "gpt-x", "type": "model", "ref": {...}}, ...]')
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)


class BenchmarkCandidateResultModel(Base, IdMixin):
    __tablename__ = "ep_benchmark_candidate_results"

    benchmark_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_benchmark_runs.id"), nullable=False, index=True)
    candidate_label: Mapped[str] = mapped_column(String(120), nullable=False)
    metric_results: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    aggregate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    item_count: Mapped[int] = mapped_column(default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(default=0, nullable=False)
