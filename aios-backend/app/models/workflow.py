from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class WorkflowModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "workflows"

    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    definition: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class WorkflowExecutionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "workflow_executions"

    workflow_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(36), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
