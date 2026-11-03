"""Failure Analysis & Risk Analysis schema: recurring failure patterns
(regression, root cause, flaky test, performance regression, memory
leak, concurrency issue, infrastructure issue) tracked with an
occurrence counter and a first/last-seen window, and risk assessments
scoring a subject (a release, a service, a workflow) against those
patterns plus other signals."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class FailurePatternModel(IdMixin, AuditMixin, Base):
    __tablename__ = "qa_failure_patterns"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pattern_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class RiskAssessmentModel(IdMixin, Base):
    __tablename__ = "qa_risk_assessments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    factors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
