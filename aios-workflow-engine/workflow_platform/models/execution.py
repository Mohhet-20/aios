"""ExecutionModel: one run of a workflow (against a specific, immutable
`WorkflowVersionModel`). `context_variables` is the live, ephemeral
per-run state the Execution Engine reads/writes as it walks the graph —
orthogonal to the persistent, longer-lived `VariableModel` rows (see
`domain/enums.py`'s module docstring). `parent_execution_id` +
`recursion_depth` support nested/recursive workflow invocation with a
real depth guard (`RecursionLimitExceededError`)."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin, utcnow
from workflow_platform.domain.enums import ExecutionStatus, TriggerType, WorkflowPriority


class ExecutionModel(Base, IdMixin):
    __tablename__ = "wf_executions"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_workflows.id"), nullable=False, index=True)
    workflow_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_workflow_versions.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_workspaces.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.PENDING.value, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default=WorkflowPriority.NORMAL.value, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(20), default=TriggerType.MANUAL.value, nullable=False)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    input_variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    context_variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Live shared execution-context state, read/written as the graph is walked")

    current_node_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    parent_execution_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("wf_executions.id"), nullable=True, index=True)
    recursion_depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timeout_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NodeExecutionModel(Base, IdMixin):
    __tablename__ = "wf_node_executions"

    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_executions.id"), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    input_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
