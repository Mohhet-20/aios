"""Reporting Platform schema: a report definition (what kind of
report, in what format, on what schedule) and a report run history
(one row per generation attempt, guarded queued -> generating ->
completed/failed) — the same split every prior AIOS platform uses
between a reusable "job config" and its individual executions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from analytics_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class ReportDefinitionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "an_report_definitions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    report_format: Mapped[str] = mapped_column(String(10), nullable=False, default="json")
    schedule: Mapped[str] = mapped_column(String(10), nullable=False, default="none")
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)


class ReportRunModel(IdMixin, Base):
    __tablename__ = "an_report_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_definition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    output: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
