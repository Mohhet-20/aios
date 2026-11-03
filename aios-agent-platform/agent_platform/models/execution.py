"""AgentExecutionModel is the observability backbone — one row per agent
"turn" (a single model-call-driven unit of work against a task),
mirroring the Prompt Platform's PromptExecutionLogModel exactly on
purpose so the same kind of latency/cost/success-rate rollups apply.
ExecutionCheckpointModel is the primitive "Interruptible execution" and
"Recovery after failure" (both explicitly in-scope under ORCHESTRATION,
unlike the full Workflow Engine) are built on.
"""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import Base, IdMixin, utcnow
from agent_platform.domain.enums import ExecutionStatus


class AgentExecutionModel(Base, IdMixin):
    __tablename__ = "agent_executions"

    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=True, index=True)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.RUNNING.value, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(60), nullable=True)

    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    started_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutionCheckpointModel(Base, IdMixin):
    __tablename__ = "agent_execution_checkpoints"

    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=False, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False, doc="e.g. 'before_step_3', 'pre_tool_call'")
    state: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Serialized resumable state")
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
