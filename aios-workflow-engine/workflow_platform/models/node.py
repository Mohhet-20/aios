"""WorkflowNodeModel / WorkflowEdgeModel: the actual graph for one
workflow version. Nodes are addressed by `node_key` (an author-chosen
short string, unique within the version — e.g. "call_llm",
"approve_step_1"), not by ORM UUID, because that's what edges, JSON
graph definitions, and execution state all naturally reference — the
same "human-readable join key within a scoped set of rows" pattern used
for `conversation_id`/`turn_index` in the Memory Platform."""
from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin


class WorkflowNodeModel(Base, IdMixin):
    __tablename__ = "wf_workflow_nodes"
    __table_args__ = (UniqueConstraint("workflow_version_id", "node_key", name="uq_wf_node_key_per_version"),)

    workflow_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_workflow_versions.id"), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(80), nullable=False)
    node_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    position: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{x, y} canvas position for the frontend builder")
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, doc="Overrides the node type's default when set")
    max_retries: Mapped[int | None] = mapped_column(Integer, nullable=True)


class WorkflowEdgeModel(Base, IdMixin):
    __tablename__ = "wf_workflow_edges"

    workflow_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_workflow_versions.id"), nullable=False, index=True)
    source_node_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_node_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    condition: Mapped[dict | None] = mapped_column(JSON, nullable=True, doc="Optional routing condition — a small expression evaluated against execution context; null means unconditional")
    edge_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
