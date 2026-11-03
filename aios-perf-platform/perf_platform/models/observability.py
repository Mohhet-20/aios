"""Performance observability: raw latency/throughput samples plus
benchmark runs that prove a specific optimization's impact with real
before/after numbers (see performance/benchmark_service.py)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from perf_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin
from perf_platform.domain.enums import JobStatus


class LatencySampleModel(IdMixin, AuditMixin, Base):
    __tablename__ = "perf_latency_samples"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ThroughputSampleModel(IdMixin, AuditMixin, Base):
    __tablename__ = "perf_throughput_samples"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BenchmarkRunModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "perf_benchmark_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=JobStatus.QUEUED.value, index=True)
    baseline_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    optimized_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    improvement_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
