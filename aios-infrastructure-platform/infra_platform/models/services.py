"""Infra service registry — a lightweight record of every runtime
service this platform tracks (API, worker, background job, scheduler,
database, cache, queue, vector DB, model server, inference service,
storage, CDN, gateway, load balancer, edge node, GPU/CPU worker),
independent of which Kubernetes resources or cloud resources actually
back it (see `kubernetes.py`/`cloud.py` for those)."""
from __future__ import annotations

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class ServiceModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_services"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    service_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="provisioning", index=True)
    cluster_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    namespace: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    replicas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    compute_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cpu_request: Mapped[str | None] = mapped_column(String(20), nullable=True)
    memory_request: Mapped[str | None] = mapped_column(String(20), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
