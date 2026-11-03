"""MetricDefinitionModel: the DB-facing catalog of every computable
metric — seeded from the in-code `metrics/registry.py` (the actual
computation functions live there; this table is what a Quality
Scorecard UI queries to list/describe available metrics without
importing Python). `MetricResultModel` is a standalone metric
computation record for callers that want to score something outside a
full evaluation run (e.g. an ad-hoc groundedness check on one
response)."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from eval_platform.database.base import Base, IdMixin, utcnow


class MetricDefinitionModel(Base, IdMixin):
    __tablename__ = "ep_metric_definitions"

    key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)
    higher_is_better: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class MetricResultModel(Base, IdMixin):
    __tablename__ = "ep_metric_results"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False, doc='e.g. "evaluation_item", "adhoc"')
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
