"""AnalyticsSnapshotModel: a persisted rollup for a workspace over a
time window (trend/quality/reliability/cost/usage/regression) — what a
historical report or executive dashboard reads instead of recomputing
from raw events every time. `RecommendationModel` is the AI Improvement
Loop's output: a concrete, evidenced suggestion tied to a target
(prompt/agent/workflow/dataset)."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from eval_platform.database.base import Base, IdMixin, utcnow
from eval_platform.domain.enums import RecommendationStatus


class AnalyticsSnapshotModel(Base, IdMixin):
    __tablename__ = "ep_analytics_snapshots"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    period_start = mapped_column(DateTime(timezone=True), nullable=False)
    period_end = mapped_column(DateTime(timezone=True), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RecommendationModel(Base, IdMixin):
    __tablename__ = "ep_recommendations"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False, doc='e.g. "prompt", "agent", "workflow", "dataset"')
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Real data backing the suggestion — failed run ids, score deltas, cluster membership")
    status: Mapped[str] = mapped_column(String(20), default=RecommendationStatus.OPEN.value, nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
