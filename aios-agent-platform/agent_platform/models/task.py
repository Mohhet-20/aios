"""TaskModel is both "a task" and, at the root of its own subtree
(`parent_task_id IS NULL`), "the plan" — a goal decomposes into subtasks
which are themselves TaskModel rows linked by `parent_task_id`, so the
task tree *is* the plan rather than a separately-modeled concept.
`depth` + `root_task_id` exist specifically so recursion-depth limits and
"which overall goal does this belong to" are O(1) lookups, not a
recursive query, during hot-path orchestration.
"""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agent_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from agent_platform.domain.enums import OrchestrationStrategy, TaskPriority, TaskStatus


class TaskModel(Base, IdMixin, AuditMixin):
    __tablename__ = "agent_tasks"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_workspaces.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)

    parent_task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=True, index=True)
    root_task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, doc="Self-referential id on the root task")
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING.value, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default=TaskPriority.NORMAL.value, nullable=False)
    orchestration_strategy: Mapped[str] = mapped_column(String(20), default=OrchestrationStrategy.SEQUENTIAL.value, nullable=False)

    assigned_agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)

    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    resource_estimate: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{estimated_tokens, estimated_cost_usd, estimated_duration_s}")
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class TaskDependencyModel(Base, IdMixin):
    """DAG edge: `task_id` depends on `depends_on_task_id` completing
    first — used for execution ordering (topological sort) independent
    of the parent/child decomposition tree."""

    __tablename__ = "agent_task_dependencies"

    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=False, index=True)
    depends_on_task_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_tasks.id"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
