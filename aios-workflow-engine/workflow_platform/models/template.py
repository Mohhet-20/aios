"""WorkflowTemplateModel: reusable starting points for the Workflow
Builder frontend — a `workspace_id` of null marks a global/marketplace
template visible to every workspace."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin, utcnow


class WorkflowTemplateModel(Base, IdMixin):
    __tablename__ = "wf_workflow_templates"

    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    graph_definition: Mapped[dict] = mapped_column(JSON, nullable=False, doc="{'nodes': [...], 'edges': [...]} — the same shape WorkflowVersionService materializes into real rows")
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
