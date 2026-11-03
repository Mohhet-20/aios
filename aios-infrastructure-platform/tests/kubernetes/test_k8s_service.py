"""Tests for the Kubernetes control-plane services: clusters, node
pools, namespaces, resource quotas, generic resource apply/upsert with
quota enforcement, and autoscaler configs."""
from __future__ import annotations

import pytest

from infra_platform.config.settings import Settings
from infra_platform.core.exceptions import (
    ClusterNotFoundError,
    ClusterNotHealthyError,
    NamespaceError,
    ResourceQuotaExceededError,
    ValidationError,
)
from infra_platform.kubernetes.k8s_service import (
    AutoscalerService,
    ClusterService,
    K8sResourceService,
    NamespaceService,
    NodePoolService,
    ResourceQuotaService,
)

TENANT = "tenant-k8s"


async def _healthy_cluster(cluster_service: ClusterService):
    cluster = await cluster_service.create_cluster(TENANT, name="prod", provider="aws", region="us-east-1")
    assert cluster.status == "provisioning"
    return await cluster_service.mark_healthy(TENANT, cluster.id)


@pytest.mark.asyncio
async def test_cluster_lifecycle(repos):
    service = ClusterService(repos)
    cluster = await service.create_cluster(TENANT, name="staging", provider="gcp", region="us-central1")
    assert cluster.status == "provisioning"

    cluster = await service.mark_healthy(TENANT, cluster.id)
    assert cluster.status == "healthy"

    cluster = await service.mark_degraded(TENANT, cluster.id)
    assert cluster.status == "degraded"

    cluster = await service.mark_unhealthy(TENANT, cluster.id)
    assert cluster.status == "unhealthy"

    cluster = await service.decommission(TENANT, cluster.id)
    assert cluster.status == "decommissioned"

    from infra_platform.core.exceptions import InvalidTransitionError
    with pytest.raises(InvalidTransitionError):
        await service.mark_healthy(TENANT, cluster.id)


@pytest.mark.asyncio
async def test_cluster_wrong_tenant_raises_not_found(repos):
    service = ClusterService(repos)
    cluster = await service.create_cluster(TENANT, name="isolated", provider="azure", region="eastus")
    with pytest.raises(ClusterNotFoundError):
        await service.get("other-tenant", cluster.id)


@pytest.mark.asyncio
async def test_node_pool_scale_within_bounds(repos):
    cluster_service = ClusterService(repos)
    pool_service = NodePoolService(repos)
    cluster = await _healthy_cluster(cluster_service)

    pool = await pool_service.add_node_pool(
        TENANT, cluster.id, name="cpu-pool", instance_type="m5.xlarge", min_nodes=2, max_nodes=8
    )
    assert pool.current_nodes == 2

    pool = await pool_service.scale_node_pool(TENANT, pool.id, target_nodes=6)
    assert pool.current_nodes == 6

    with pytest.raises(ValidationError):
        await pool_service.scale_node_pool(TENANT, pool.id, target_nodes=20)


@pytest.mark.asyncio
async def test_node_pool_requires_existing_cluster(repos):
    pool_service = NodePoolService(repos)
    with pytest.raises(ClusterNotFoundError):
        await pool_service.add_node_pool(TENANT, "no-such-cluster", name="gpu-pool", instance_type="p3.2xlarge")


@pytest.mark.asyncio
async def test_namespace_create_and_duplicate_rejected(repos):
    cluster_service = ClusterService(repos)
    ns_service = NamespaceService(repos)
    cluster = await _healthy_cluster(cluster_service)

    ns = await ns_service.create_namespace(TENANT, cluster.id, name="team-a")
    assert ns.name == "team-a"

    with pytest.raises(NamespaceError):
        await ns_service.create_namespace(TENANT, cluster.id, name="team-a")


@pytest.mark.asyncio
async def test_namespace_defaults_from_settings(repos):
    cluster_service = ClusterService(repos)
    ns_service = NamespaceService(repos, settings=Settings(default_namespace="platform-default"))
    cluster = await _healthy_cluster(cluster_service)
    ns = await ns_service.create_namespace(TENANT, cluster.id)
    assert ns.name == "platform-default"


@pytest.mark.asyncio
async def test_apply_resource_create_then_update_upsert(repos):
    cluster_service = ClusterService(repos)
    resource_service = K8sResourceService(repos)
    cluster = await _healthy_cluster(cluster_service)

    resource = await resource_service.apply_resource(
        TENANT, cluster.id, namespace="default", kind="deployment", name="api",
        spec={"image": "aios/api:1.0.0"}, replicas=3,
    )
    assert resource.status == "pending"
    assert resource.replicas == 3

    resource = await resource_service.apply_resource(
        TENANT, cluster.id, namespace="default", kind="deployment", name="api",
        spec={"image": "aios/api:1.1.0"}, replicas=5,
    )
    assert resource.status == "updating"
    assert resource.replicas == 5
    assert resource.spec["image"] == "aios/api:1.1.0"

    all_resources = await resource_service.list_for_namespace(TENANT, cluster.id, "default")
    assert len(all_resources) == 1  # upsert, not a duplicate row


@pytest.mark.asyncio
async def test_apply_resource_blocked_on_unhealthy_cluster(repos):
    cluster_service = ClusterService(repos)
    resource_service = K8sResourceService(repos)
    cluster = await _healthy_cluster(cluster_service)
    cluster = await cluster_service.mark_unhealthy(TENANT, cluster.id)

    with pytest.raises(ClusterNotHealthyError):
        await resource_service.apply_resource(
            TENANT, cluster.id, namespace="default", kind="deployment", name="api", spec={}
        )


@pytest.mark.asyncio
async def test_resource_quota_enforcement(repos):
    cluster_service = ClusterService(repos)
    quota_service = ResourceQuotaService(repos)
    resource_service = K8sResourceService(repos)
    cluster = await _healthy_cluster(cluster_service)

    await quota_service.set_quota(TENANT, cluster.id, "default", cpu_limit="4", memory_limit="8Gi")

    await resource_service.apply_resource(
        TENANT, cluster.id, namespace="default", kind="deployment", name="svc-a",
        spec={"cpu_request": 2, "memory_request_gi": 4},
    )

    # svc-b would push cpu usage to 2 + 3 = 5 > 4 limit
    with pytest.raises(ResourceQuotaExceededError):
        await resource_service.apply_resource(
            TENANT, cluster.id, namespace="default", kind="deployment", name="svc-b",
            spec={"cpu_request": 3, "memory_request_gi": 1},
        )

    # within bounds succeeds
    resource = await resource_service.apply_resource(
        TENANT, cluster.id, namespace="default", kind="deployment", name="svc-c",
        spec={"cpu_request": 1, "memory_request_gi": 1},
    )
    assert resource.status == "pending"


@pytest.mark.asyncio
async def test_resource_quota_update_excludes_own_prior_usage(repos):
    cluster_service = ClusterService(repos)
    quota_service = ResourceQuotaService(repos)
    resource_service = K8sResourceService(repos)
    cluster = await _healthy_cluster(cluster_service)
    await quota_service.set_quota(TENANT, cluster.id, "default", cpu_limit="4", memory_limit="8Gi")

    await resource_service.apply_resource(
        TENANT, cluster.id, namespace="default", kind="deployment", name="svc-a",
        spec={"cpu_request": 3, "memory_request_gi": 2},
    )
    # re-applying svc-a with the same request should not double count against itself
    resource = await resource_service.apply_resource(
        TENANT, cluster.id, namespace="default", kind="deployment", name="svc-a",
        spec={"cpu_request": 3, "memory_request_gi": 2},
    )
    assert resource.status == "updating"


@pytest.mark.asyncio
async def test_scale_and_delete_resource(repos):
    cluster_service = ClusterService(repos)
    resource_service = K8sResourceService(repos)
    cluster = await _healthy_cluster(cluster_service)

    resource = await resource_service.apply_resource(
        TENANT, cluster.id, namespace="default", kind="deployment", name="worker", spec={}, replicas=1
    )
    resource = await resource_service.scale_resource(TENANT, resource.id, replicas=4)
    assert resource.replicas == 4

    with pytest.raises(ValidationError):
        await resource_service.scale_resource(TENANT, resource.id, replicas=-1)

    resource = await resource_service.mark_running(TENANT, resource.id)
    assert resource.status == "running"

    await resource_service.delete_resource(TENANT, resource.id)
    remaining = await resource_service.list_for_namespace(TENANT, cluster.id, "default")
    assert all(r.id != resource.id for r in remaining)


@pytest.mark.asyncio
async def test_autoscaler_defaults_and_bounds(repos):
    cluster_service = ClusterService(repos)
    autoscaler_service = AutoscalerService(repos, settings=Settings(hpa_default_min_replicas=2, hpa_default_max_replicas=10))
    cluster = await _healthy_cluster(cluster_service)

    autoscaler = await autoscaler_service.create_autoscaler(
        TENANT, cluster.id, namespace="default", target_resource_name="api", target_cpu_percent=70
    )
    assert autoscaler.min_replicas == 2
    assert autoscaler.max_replicas == 10

    autoscaler = await autoscaler_service.update_targets(TENANT, autoscaler.id, min_replicas=3, max_replicas=6)
    assert (autoscaler.min_replicas, autoscaler.max_replicas) == (3, 6)

    with pytest.raises(ValidationError):
        await autoscaler_service.update_targets(TENANT, autoscaler.id, min_replicas=9, max_replicas=6)
