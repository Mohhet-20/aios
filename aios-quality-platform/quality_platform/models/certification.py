"""Release Certification Engine schema: one run per release
certification attempt (guarded queued -> running -> completed/failed),
combining the quality/reliability/security/performance/AI-quality
scores into an overall score and a deployment decision, with the full
generated report kept alongside for audit."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class CertificationRunModel(IdMixin, AuditMixin, Base):
    __tablename__ = "qa_certification_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    release_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    security_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    performance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    report: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
