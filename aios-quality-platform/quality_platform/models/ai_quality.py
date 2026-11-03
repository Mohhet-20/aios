"""AI Quality / Evaluation Regression Engine schema: a baseline score
per (dimension, subject), raw evaluation scores over time, and
regression scans (guarded queued -> running -> completed/failed) that
compare a fresh evaluation against its baseline and record the
severity of any drift."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class AiQualityBaselineModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "qa_ai_quality_baselines"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    baseline_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AiQualityEvaluationModel(IdMixin, Base):
    __tablename__ = "qa_ai_quality_evaluations"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class RegressionScanModel(IdMixin, AuditMixin, Base):
    __tablename__ = "qa_regression_scans"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    baseline_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    delta_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="none")
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
