"""ExecutionCheckpointModel: a replay point for BATCH/long-running tool
executions — same role as the Workflow Engine's CheckpointModel, scoped
to a single tool execution instead of a whole workflow run."""
from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import Base, IdMixin


class ExecutionCheckpointModel(Base, IdMixin):
    __tablename__ = "tp_execution_checkpoints"

    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_tool_executions.id"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
