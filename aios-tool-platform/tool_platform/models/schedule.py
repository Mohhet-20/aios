"""ToolScheduleModel: how a tool gets invoked without something calling
`POST /executions` directly — immediate/delayed/recurring/cron/calendar,
with concurrency and rate limits, mirroring the Workflow Engine's
ScheduleModel exactly (same dispatcher shape, scoped to a tool instead
of a workflow)."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import Base, IdMixin, utcnow
from tool_platform.domain.enums import Priority, ScheduleStatus


class ToolScheduleModel(Base, IdMixin):
    __tablename__ = "tp_tool_schedules"

    tool_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_tools.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    cron_expression: Mapped[str | None] = mapped_column(String(120), nullable=True)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, doc="For DELAYED/CALENDAR one-shot schedules")

    status: Mapped[str] = mapped_column(String(20), default=ScheduleStatus.ACTIVE.value, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default=Priority.NORMAL.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    max_concurrent_executions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)

    next_run_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    last_execution_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
