"""ToolExecutionModel: one record per tool invocation, across every
execution mode (sync/async/streaming/batch/parallel/queued/scheduled).
`parent_execution_id` links a BATCH/PARALLEL sub-call back to whatever
kicked it off, mirroring the Workflow Engine's nested-execution pattern.
`sandbox_usage` holds whatever the sandbox genuinely measured (CPU
seconds, peak memory, disk, network bytes) — see the observability
module's honesty principle: fields are only ever populated from a real
measurement, never estimated."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import Base, IdMixin, utcnow
from tool_platform.domain.enums import ExecutionMode, ExecutionStatus, Priority


class ToolExecutionModel(Base, IdMixin):
    __tablename__ = "tp_tool_executions"

    tool_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_tools.id"), nullable=False, index=True)
    tool_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_tool_versions.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_execution_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tp_tool_executions.id"), nullable=True, index=True)

    execution_mode: Mapped[str] = mapped_column(String(20), default=ExecutionMode.SYNC.value, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.PENDING.value, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default=Priority.NORMAL.value, nullable=False)

    input_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    retry_backoff_seconds: Mapped[float] = mapped_column(Float, default=1.5, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    credential_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    trigger_type: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)

    sandbox_usage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Genuinely-measured resource usage: cpu_seconds, peak_memory_mb, disk_mb, network_bytes")
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
