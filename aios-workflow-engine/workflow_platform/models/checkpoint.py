"""CheckpointModel: a durable snapshot of execution state taken after
every node completes, so `pause`/`resume`/crash-recovery can restore an
execution to exactly where it left off rather than re-running from the
start. `sequence_number` gives a strict ordering independent of
wall-clock time (two checkpoints in the same millisecond still sort
correctly)."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin, utcnow


class CheckpointModel(Base, IdMixin):
    __tablename__ = "wf_checkpoints"

    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_executions.id"), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(80), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, doc="Full execution context/variables + completed-node set at this point")
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
