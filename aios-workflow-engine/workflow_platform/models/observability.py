"""ExecutionLogModel: the structured log stream for one execution —
distinct from `NodeExecutionModel`'s status/timing columns (which answer
"what happened to this node"), this answers "what did this node/execution
print/report along the way" — the raw material for the Execution Timeline
and Execution Log frontend surfaces."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin, utcnow
from workflow_platform.domain.enums import LogLevel


class ExecutionLogModel(Base, IdMixin):
    __tablename__ = "wf_execution_logs"

    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_executions.id"), nullable=False, index=True)
    node_execution_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("wf_node_executions.id"), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(20), default=LogLevel.INFO.value, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    log_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
