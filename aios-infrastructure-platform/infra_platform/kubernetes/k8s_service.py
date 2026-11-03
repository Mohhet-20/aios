"""Kubernetes control plane: clusters, node pools, namespaces, generic
K8s resources (polymorphic single-table over `kind`), resource quotas,
and HPA/VPA autoscaler configs.

DISCLOSED SCOPE BOUNDARY (see models/kubernetes.py docstring): this is
a control plane that models and tracks K8s concepts — it does not
hold a real kubeconfig or talk to a live API server. `apply_resource`
is exactly the seam where a real reconciliation loop would plug in.

Resource quota enforcement is deliberately simple: `spec` may carry
`cpu_request` (int cores) and `memory_request_gi` (int GiB); applying
a resource sums requests already committed in the namespace against
the namespace's `ResourceQuotaModel` limits and blocks the request
with `ResourceQuotaExceededError` if it would push the namespace over
either limit. Namespaces with no quota configured are unbounded.

`apply_resource`'s upsert-by-identity (cluster, namespace, kind, name)
is a check-then-act sequence spanning multiple statements (look up
existing -> quota check -> insert-or-update -> commit); two concurrent
applies of the same brand-new resource could otherwise both see "no
existing row" and both insert, producing a duplicate. The whole
sequence is serialized per (tenant, cluster, namespace, kind, name)
with an in-process `asyncio.Lock`, the same commit-spanning-lock
pattern used throughout the AIOS build (e.g. the Security Platform's
`GovernanceAssetService.register_asset`)."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from infra_platform.config.settings import Settings, get_settings
from infra_platform.core.exceptions import (
    ClusterNotFoundError,
    ClusterNotHealthyError,
    NamespaceError,
    ResourceQuotaExceededError,
    ValidationError,
)
from infra_platform.domain.entities import Cluster as ClusterEntity
from infra_platform.domain.enums import ClusterStatus
from infra_platform.models.kubernetes import (
    AutoscalerConfigModel,
    ClusterModel,
    K8sResourceModel,
    NamespaceModel,
    NodePoolModel,
    ResourceQuotaModel,
)
from infra_platform.repositories.registry import RepositoryRegistry


def _to_cluster_entity(model: ClusterModel) -> ClusterEntity:
    return ClusterEntity(id=model.id, status=ClusterStatus(model.status))


def _parse_cpu(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _parse_memory_gi(value: str) -> int:
    try:
        return int(float(value.rstrip("GiMi")))
    except (TypeError, ValueError):
        return 0


class ClusterService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_cluster(
        self, tenant_id: str, *, name: str, provider: str, region: str, kubernetes_version: str = "1.30"
    ) -> ClusterModel:
        cluster = ClusterModel(
            tenant_id=tenant_id, name=name, provider=provider, region=region,
            status=ClusterStatus.PROVISIONING.value, kubernetes_version=kubernetes_version, node_count=0,
        )
        return await self.repos.clusters.add(cluster)

    async def get(self, tenant_id: str, cluster_id: str) -> ClusterModel:
        cluster = await self.repos.clusters.get(cluster_id)
        if cluster is None or cluster.tenant_id != tenant_id:
            raise ClusterNotFoundError(f"Cluster '{cluster_id}' not found")
        return cluster

    async def _transition(self, tenant_id: str, cluster_id: str, action: str) -> ClusterModel:
        cluster = await self.get(tenant_id, cluster_id)
        entity = _to_cluster_entity(cluster)
        getattr(entity, action)()
        cluster.status = entity.status.value
        return await self.repos.clusters.update(cluster)

    async def mark_healthy(self, tenant_id: str, cluster_id: str) -> ClusterModel:
        return await self._transition(tenant_id, cluster_id, "mark_healthy")

    async def mark_degraded(self, tenant_id: str, cluster_id: str) -> ClusterModel:
        return await self._transition(tenant_id, cluster_id, "mark_degraded")

    async def mark_unhealthy(self, tenant_id: str, cluster_id: str) -> ClusterModel:
        return await self._transition(tenant_id, cluster_id, "mark_unhealthy")

    async def decommission(self, tenant_id: str, cluster_id: str) -> ClusterModel:
        return await self._transition(tenant_id, cluster_id, "decommission")

    async def list_for_tenant(self, tenant_id: str) -> list[ClusterModel]:
        return await self.repos.clusters.list_for_tenant(tenant_id)


class NodePoolService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_node_pool(
        self, tenant_id: str, cluster_id: str, *, name: str, pool_type: str = "cpu",
        instance_type: str, min_nodes: int = 1, max_nodes: int = 5, gpu_type: str | None = None,
    ) -> NodePoolModel:
        cluster = await self.repos.clusters.get(cluster_id)
        if cluster is None or cluster.tenant_id != tenant_id:
            raise ClusterNotFoundError(f"Cluster '{cluster_id}' not found")
        if min_nodes > max_nodes:
            raise ValidationError("min_nodes cannot exceed max_nodes")
        pool = NodePoolModel(
            tenant_id=tenant_id, cluster_id=cluster_id, name=name, pool_type=pool_type,
            instance_type=instance_type, min_nodes=min_nodes, max_nodes=max_nodes,
            current_nodes=min_nodes, gpu_type=gpu_type,
        )
        return await self.repos.node_pools.add(pool)

    async def scale_node_pool(self, tenant_id: str, pool_id: str, *, target_nodes: int) -> NodePoolModel:
        pool = await self.repos.node_pools.get_or_404(pool_id)
        if pool.tenant_id != tenant_id:
            raise ClusterNotFoundError(f"NodePool '{pool_id}' not found")
        if not (pool.min_nodes <= target_nodes <= pool.max_nodes):
            raise ValidationError(
                f"target_nodes {target_nodes} outside pool bounds [{pool.min_nodes}, {pool.max_nodes}]"
            )
        pool.current_nodes = target_nodes
        return await self.repos.node_pools.update(pool)

    async def list_for_cluster(self, tenant_id: str, cluster_id: str) -> list[NodePoolModel]:
        return await self.repos.node_pools.list_for_cluster(tenant_id, cluster_id)


class NamespaceService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_namespace(
        self, tenant_id: str, cluster_id: str, *, name: str | None = None, labels: dict | None = None
    ) -> NamespaceModel:
        cluster = await self.repos.clusters.get(cluster_id)
        if cluster is None or cluster.tenant_id != tenant_id:
            raise ClusterNotFoundError(f"Cluster '{cluster_id}' not found")
        ns_name = name or self.settings.default_namespace
        existing = await self.repos.namespaces.get_by_name(tenant_id, cluster_id, ns_name)
        if existing is not None:
            raise NamespaceError(f"Namespace '{ns_name}' already exists in cluster '{cluster_id}'")
        namespace = NamespaceModel(tenant_id=tenant_id, cluster_id=cluster_id, name=ns_name, labels=labels or {})
        return await self.repos.namespaces.add(namespace)

    async def list_for_cluster(self, tenant_id: str, cluster_id: str) -> list[NamespaceModel]:
        return await self.repos.namespaces.list_for_cluster(tenant_id, cluster_id)


class ResourceQuotaService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def set_quota(
        self, tenant_id: str, cluster_id: str, namespace: str, *,
        cpu_limit: str | None = None, memory_limit: str | None = None, gpu_limit: str | None = None,
    ) -> ResourceQuotaModel:
        existing = await self.repos.resource_quotas.get_for_namespace(tenant_id, cluster_id, namespace)
        if existing is not None:
            existing.cpu_limit = cpu_limit or existing.cpu_limit
            existing.memory_limit = memory_limit or existing.memory_limit
            existing.gpu_limit = gpu_limit if gpu_limit is not None else existing.gpu_limit
            return await self.repos.resource_quotas.update(existing)
        quota = ResourceQuotaModel(
            tenant_id=tenant_id, cluster_id=cluster_id, namespace=namespace,
            cpu_limit=cpu_limit or self.settings.default_resource_quota_cpu,
            memory_limit=memory_limit or self.settings.default_resource_quota_memory,
            gpu_limit=gpu_limit,
        )
        return await self.repos.resource_quotas.add(quota)

    async def get_for_namespace(self, tenant_id: str, cluster_id: str, namespace: str) -> ResourceQuotaModel | None:
        return await self.repos.resource_quotas.get_for_namespace(tenant_id, cluster_id, namespace)


class K8sResourceService:
    """Applies (creates or updates) generic K8s resources with quota
    enforcement, mirroring `kubectl apply`'s upsert-by-identity
    semantics keyed on (cluster, namespace, kind, name)."""

    _apply_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def _usage_excluding(
        self, tenant_id: str, cluster_id: str, namespace: str, exclude_id: str | None
    ) -> tuple[int, int]:
        resources = await self.repos.k8s_resources.list_for_namespace(tenant_id, cluster_id, namespace)
        cpu_used = 0
        mem_used = 0
        for r in resources:
            if r.id == exclude_id:
                continue
            cpu_used += int(r.spec.get("cpu_request", 0) or 0)
            mem_used += int(r.spec.get("memory_request_gi", 0) or 0)
        return cpu_used, mem_used

    async def apply_resource(
        self, tenant_id: str, cluster_id: str, *, namespace: str, kind: str, name: str,
        spec: dict | None = None, replicas: int | None = None,
    ) -> K8sResourceModel:
        lock_key = f"{tenant_id}:{cluster_id}:{namespace}:{kind}:{name}"
        async with self._apply_locks[lock_key]:
            cluster = await self.repos.clusters.get(cluster_id)
            if cluster is None or cluster.tenant_id != tenant_id:
                raise ClusterNotFoundError(f"Cluster '{cluster_id}' not found")
            if cluster.status in (ClusterStatus.UNHEALTHY.value, ClusterStatus.DECOMMISSIONED.value):
                raise ClusterNotHealthyError(f"Cluster '{cluster_id}' is {cluster.status}; refusing to apply resources")

            spec = spec or {}
            existing = await self.repos.k8s_resources.get_by_kind_name(tenant_id, cluster_id, namespace, kind, name)

            quota = await self.repos.resource_quotas.get_for_namespace(tenant_id, cluster_id, namespace)
            if quota is not None:
                cpu_used, mem_used = await self._usage_excluding(
                    tenant_id, cluster_id, namespace, existing.id if existing else None
                )
                requested_cpu = int(spec.get("cpu_request", 0) or 0)
                requested_mem = int(spec.get("memory_request_gi", 0) or 0)
                cpu_limit = _parse_cpu(quota.cpu_limit)
                mem_limit = _parse_memory_gi(quota.memory_limit)
                if cpu_used + requested_cpu > cpu_limit or mem_used + requested_mem > mem_limit:
                    raise ResourceQuotaExceededError(
                        f"Applying '{kind}/{name}' would exceed namespace '{namespace}' quota "
                        f"(cpu {cpu_used + requested_cpu}/{cpu_limit}, memory {mem_used + requested_mem}Gi/{mem_limit}Gi)"
                    )

            if existing is not None:
                existing.spec = spec
                if replicas is not None:
                    existing.replicas = replicas
                existing.status = "updating"
                result = await self.repos.k8s_resources.update(existing)
                await self.repos.session.commit()
                return result

            resource = K8sResourceModel(
                tenant_id=tenant_id, cluster_id=cluster_id, namespace=namespace, kind=kind, name=name,
                spec=spec, status="pending", replicas=replicas,
            )
            result = await self.repos.k8s_resources.add(resource)
            await self.repos.session.commit()
            return result

    async def mark_running(self, tenant_id: str, resource_id: str) -> K8sResourceModel:
        resource = await self.repos.k8s_resources.get_or_404(resource_id)
        if resource.tenant_id != tenant_id:
            raise ClusterNotFoundError(f"Resource '{resource_id}' not found")
        resource.status = "running"
        return await self.repos.k8s_resources.update(resource)

    async def scale_resource(self, tenant_id: str, resource_id: str, *, replicas: int) -> K8sResourceModel:
        resource = await self.repos.k8s_resources.get_or_404(resource_id)
        if resource.tenant_id != tenant_id:
            raise ClusterNotFoundError(f"Resource '{resource_id}' not found")
        if replicas < 0:
            raise ValidationError("replicas cannot be negative")
        resource.replicas = replicas
        return await self.repos.k8s_resources.update(resource)

    async def delete_resource(self, tenant_id: str, resource_id: str) -> None:
        resource = await self.repos.k8s_resources.get_or_404(resource_id)
        if resource.tenant_id != tenant_id:
            raise ClusterNotFoundError(f"Resource '{resource_id}' not found")
        await self.repos.k8s_resources.delete(resource)

    async def list_for_namespace(self, tenant_id: str, cluster_id: str, namespace: str) -> list[K8sResourceModel]:
        return await self.repos.k8s_resources.list_for_namespace(tenant_id, cluster_id, namespace)


class AutoscalerService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_autoscaler(
        self, tenant_id: str, cluster_id: str, *, namespace: str, target_resource_name: str, kind: str = "hpa",
        min_replicas: int | None = None, max_replicas: int | None = None,
        target_cpu_percent: int | None = None, target_memory_percent: int | None = None,
    ) -> AutoscalerConfigModel:
        cluster = await self.repos.clusters.get(cluster_id)
        if cluster is None or cluster.tenant_id != tenant_id:
            raise ClusterNotFoundError(f"Cluster '{cluster_id}' not found")
        min_r = min_replicas if min_replicas is not None else self.settings.hpa_default_min_replicas
        max_r = max_replicas if max_replicas is not None else self.settings.hpa_default_max_replicas
        if min_r > max_r:
            raise ValidationError("min_replicas cannot exceed max_replicas")
        autoscaler = AutoscalerConfigModel(
            tenant_id=tenant_id, cluster_id=cluster_id, namespace=namespace, target_resource_name=target_resource_name,
            kind=kind, min_replicas=min_r, max_replicas=max_r,
            target_cpu_percent=target_cpu_percent, target_memory_percent=target_memory_percent,
        )
        return await self.repos.autoscaler_configs.add(autoscaler)

    async def update_targets(
        self, tenant_id: str, autoscaler_id: str, *, min_replicas: int | None = None, max_replicas: int | None = None
    ) -> AutoscalerConfigModel:
        autoscaler = await self.repos.autoscaler_configs.get_or_404(autoscaler_id)
        if autoscaler.tenant_id != tenant_id:
            raise ClusterNotFoundError(f"Autoscaler '{autoscaler_id}' not found")
        new_min = min_replicas if min_replicas is not None else autoscaler.min_replicas
        new_max = max_replicas if max_replicas is not None else autoscaler.max_replicas
        if new_min > new_max:
            raise ValidationError("min_replicas cannot exceed max_replicas")
        autoscaler.min_replicas = new_min
        autoscaler.max_replicas = new_max
        return await self.repos.autoscaler_configs.update(autoscaler)

    async def list_for_cluster(self, tenant_id: str, cluster_id: str) -> list[AutoscalerConfigModel]:
        return await self.repos.autoscaler_configs.list_for_cluster(tenant_id, cluster_id)
