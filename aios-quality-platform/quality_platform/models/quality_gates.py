"""Quality Gates & Coverage Platform schema: a gate per release
(pending -> passed/failed/waived), the individual check results that
decided it (across the eight check types the prompt specifies), and
coverage snapshots across the nine coverage types the prompt
specifies."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class QualityGateModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "qa_quality_gates"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    release_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    min_score: Mapped[float] = mapped_column(Float, nullable=False, default=80.0)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending", index=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QualityGateCheckResultModel(IdMixin, Base):
    __tablename__ = "qa_quality_gate_check_results"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    quality_gate_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    check_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CoverageSnapshotModel(IdMixin, Base):
    __tablename__ = "qa_coverage_snapshots"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    coverage_type: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    covered_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
