"""API & Workflow Validation schema: API validation runs (schema,
request/response, contract, backward/version/SDK compatibility --
synchronous pass/fail checks, not long-running jobs) and workflow
validation runs (guarded queued -> running -> completed/failed,
checking the nine workflow-correctness dimensions the prompt
specifies: logic, node execution, parallel execution, retries,
compensation, timeout handling, failure recovery, approval chains,
human-in-the-loop)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from quality_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class ApiValidationRunModel(IdMixin, AuditMixin, Base):
    __tablename__ = "qa_api_validation_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    validation_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    outcome: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class WorkflowValidationRunModel(IdMixin, AuditMixin, Base):
    __tablename__ = "qa_workflow_validation_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workflow_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    checks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
