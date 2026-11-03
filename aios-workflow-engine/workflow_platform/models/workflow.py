"""WorkflowModel: the top-level workflow record — identity, ownership,
categorization, and the pointer to whichever `WorkflowVersionModel` is
currently active. `WorkflowVersionModel` is the versioned graph itself
(nodes + edges) — editing a workflow creates or updates a DRAFT version
rather than mutating a published one in place, so an in-flight execution
started against version 3 keeps running against version 3's graph even
if version 4 gets published mid-flight."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from workflow_platform.domain.enums import WorkflowPriority, WorkflowStatus, WorkflowVersionStatus


class WorkflowModel(Base, IdMixin, AuditMixin):
    __tablename__ = "wf_workflows"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=WorkflowStatus.DRAFT.value, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default=WorkflowPriority.NORMAL.value, nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("wf_workflow_versions.id"), nullable=True)
    variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Default/declared workflow-level variable schema and defaults")
    workflow_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class WorkflowVersionModel(Base, IdMixin):
    __tablename__ = "wf_workflow_versions"

    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_workflows.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=WorkflowVersionStatus.DRAFT.value, nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
