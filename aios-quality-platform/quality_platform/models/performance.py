"""Performance Testing Engine schema: one job row per performance
test run (guarded queued -> running -> completed/failed) across the
six performance test types the prompt specifies, plus per-metric
benchmark results (latency percentiles, throughput, error rate,
resource utilization) recorded against that run."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class PerformanceTestRunModel(IdMixin, AuditMixin, Base):
    __tablename__ = "qa_performance_test_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    performance_test_type: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BenchmarkResultModel(IdMixin, Base):
    __tablename__ = "qa_benchmark_results"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    performance_test_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="ms")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
