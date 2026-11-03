"""Kubernetes control-plane schema: clusters, node pools (CPU/GPU),
namespaces, generic K8s resources (Deployment/StatefulSet/DaemonSet/
Job/CronJob/Service/Ingress/ConfigMap/Secret/PersistentVolume — one
polymorphic table with a `kind` discriminator and a JSON `spec`,
rather than ten near-identical tables), resource quotas, and
HPA/VPA autoscaler configs.

DISCLOSED SCOPE BOUNDARY: this platform is a control plane that
models and tracks Kubernetes concepts — it does not itself hold a
real kubeconfig or talk to a real API server. `K8sResourceModel.spec`
is exactly the seam where a real cluster-reconciliation loop (e.g. a
controller watching this table and calling the real Kubernetes API)
would plug in, the same disclosed-gap posture as the Security
Platform's guardrail detectors being heuristic rather than ML."""
from __future__ import annotations

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class ClusterModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_clusters"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="provisioning", index=True)
    kubernetes_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.30")
    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class NodePoolModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_node_pools"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    pool_type: Mapped[str] = mapped_column(String(10), nullable=False, default="cpu")
    instance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    min_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    current_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    gpu_type: Mapped[str | None] = mapped_column(String(50), nullable=True)


class NamespaceModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_namespaces"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    labels: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class K8sResourceModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_k8s_resources"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    namespace: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    spec: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    replicas: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ResourceQuotaModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_resource_quotas"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    namespace: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    cpu_limit: Mapped[str] = mapped_column(String(20), nullable=False, default="4")
    memory_limit: Mapped[str] = mapped_column(String(20), nullable=False, default="8Gi")
    gpu_limit: Mapped[str | None] = mapped_column(String(20), nullable=True)


class AutoscalerConfigModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_autoscaler_configs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    namespace: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    target_resource_name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="hpa")
    min_replicas: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    max_replicas: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    target_cpu_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_memory_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
