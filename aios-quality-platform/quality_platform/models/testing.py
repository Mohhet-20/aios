"""Test Management & Automation schema: suites (a named grouping of
cases within one of the 15 test-pyramid types), cases, runs (guarded
queued -> running -> completed/failed), and per-case results within a
run -- the history every flaky-test/regression detector reads from."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class TestSuiteModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "qa_test_suites"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    test_type: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active", index=True)


class TestCaseModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "qa_test_cases"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    suite_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    test_type: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active", index=True)


class TestRunModel(IdMixin, AuditMixin, Base):
    __tablename__ = "qa_test_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    suite_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TestCaseResultModel(IdMixin, Base):
    __tablename__ = "qa_test_case_results"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    test_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    test_case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
