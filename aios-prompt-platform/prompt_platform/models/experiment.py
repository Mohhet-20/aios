"""A/B and multi-variant experiments."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from prompt_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from prompt_platform.domain.enums import ExperimentStatus


class ExperimentModel(Base, IdMixin, AuditMixin):
    __tablename__ = "experiments"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_workspaces.id"), nullable=False, index=True)
    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ExperimentStatus.DRAFT.value, nullable=False)
    sample_size_per_variant: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False, doc="Fixed seed for reproducibility")
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    winner_variant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ExperimentVariantModel(Base, IdMixin, AuditMixin):
    __tablename__ = "experiment_variants"

    experiment_id: Mapped[str] = mapped_column(String(36), ForeignKey("experiments.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=True)
    model_override: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_override: Mapped[str | None] = mapped_column(String(60), nullable=True)
    temperature_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    parameter_overrides: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    traffic_percent: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)


class ExperimentResultModel(Base, IdMixin):
    __tablename__ = "experiment_results"

    experiment_id: Mapped[str] = mapped_column(String(36), ForeignKey("experiments.id"), nullable=False, index=True)
    variant_id: Mapped[str] = mapped_column(String(36), ForeignKey("experiment_variants.id"), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(30), nullable=False)
    mean_score: Mapped[float] = mapped_column(Float, nullable=False)
    stddev: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_scores: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
