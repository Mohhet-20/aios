"""Service/dependency topology as a plain directed graph: nodes are
(mostly) the same components everything else references, edges record
a typed dependency between two nodes. Kept intentionally separate from
`ComponentModel` rather than merged into it — a topology node can
represent something with no independent health/alert story of its own
(e.g. an external SaaS integration point)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class TopologyNodeModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "obs_topology_nodes"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    component_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    node_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class TopologyEdgeModel(IdMixin, Base):
    __tablename__ = "obs_topology_edges"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    edge_type: Mapped[str] = mapped_column(String(30), nullable=False)
    edge_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
