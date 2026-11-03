"""Kubernetes control-plane API: clusters, node pools, namespaces,
resource quotas, generic K8s resource apply/upsert, and HPA/VPA
autoscaler configs."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.dependencies.dependencies import (
    get_cluster_service,
    get_current_tenant_id,
    get_k8s_autoscaler_service,
    get_k8s_resource_service,
    get_namespace_service,
    get_node_pool_service,
    get_resource_quota_service,
)
from infra_platform.infra_api.serialization import to_dict, to_dict_list
from infra_platform.kubernetes.k8s_service import (
    AutoscalerService,
    ClusterService,
    K8sResourceService,
    NamespaceService,
    NodePoolService,
    ResourceQuotaService,
)

router = APIRouter(prefix="/k8s", tags=["kubernetes"])


class CreateClusterRequest(BaseModel):
    name: str
    provider: str
    region: str
    kubernetes_version: str = "1.30"


@router.post("/clusters", status_code=201)
async def create_cluster(body: CreateClusterRequest, tenant_id: str = Depends(get_current_tenant_id), service: ClusterService = Depends(get_cluster_service)):
    return to_dict(await service.create_cluster(tenant_id, **body.model_dump()))


@router.get("/clusters")
async def list_clusters(tenant_id: str = Depends(get_current_tenant_id), service: ClusterService = Depends(get_cluster_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.post("/clusters/{cluster_id}/healthy")
async def mark_cluster_healthy(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ClusterService = Depends(get_cluster_service)):
    return to_dict(await service.mark_healthy(tenant_id, cluster_id))


@router.post("/clusters/{cluster_id}/degraded")
async def mark_cluster_degraded(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ClusterService = Depends(get_cluster_service)):
    return to_dict(await service.mark_degraded(tenant_id, cluster_id))


@router.post("/clusters/{cluster_id}/unhealthy")
async def mark_cluster_unhealthy(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ClusterService = Depends(get_cluster_service)):
    return to_dict(await service.mark_unhealthy(tenant_id, cluster_id))


@router.post("/clusters/{cluster_id}/decommission")
async def decommission_cluster(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ClusterService = Depends(get_cluster_service)):
    return to_dict(await service.decommission(tenant_id, cluster_id))


class AddNodePoolRequest(BaseModel):
    name: str
    pool_type: str = "cpu"
    instance_type: str
    min_nodes: int = 1
    max_nodes: int = 5
    gpu_type: str | None = None


@router.post("/clusters/{cluster_id}/node-pools", status_code=201)
async def add_node_pool(
    cluster_id: str, body: AddNodePoolRequest, tenant_id: str = Depends(get_current_tenant_id), service: NodePoolService = Depends(get_node_pool_service)
):
    return to_dict(await service.add_node_pool(tenant_id, cluster_id, **body.model_dump()))


@router.get("/clusters/{cluster_id}/node-pools")
async def list_node_pools(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: NodePoolService = Depends(get_node_pool_service)):
    return to_dict_list(await service.list_for_cluster(tenant_id, cluster_id))


class ScaleNodePoolRequest(BaseModel):
    target_nodes: int


@router.post("/node-pools/{pool_id}/scale")
async def scale_node_pool(pool_id: str, body: ScaleNodePoolRequest, tenant_id: str = Depends(get_current_tenant_id), service: NodePoolService = Depends(get_node_pool_service)):
    return to_dict(await service.scale_node_pool(tenant_id, pool_id, **body.model_dump()))


class CreateNamespaceRequest(BaseModel):
    name: str | None = None
    labels: dict | None = None


@router.post("/clusters/{cluster_id}/namespaces", status_code=201)
async def create_namespace(
    cluster_id: str, body: CreateNamespaceRequest, tenant_id: str = Depends(get_current_tenant_id), service: NamespaceService = Depends(get_namespace_service)
):
    return to_dict(await service.create_namespace(tenant_id, cluster_id, **body.model_dump()))


@router.get("/clusters/{cluster_id}/namespaces")
async def list_namespaces(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: NamespaceService = Depends(get_namespace_service)):
    return to_dict_list(await service.list_for_cluster(tenant_id, cluster_id))


class SetQuotaRequest(BaseModel):
    cpu_limit: str | None = None
    memory_limit: str | None = None
    gpu_limit: str | None = None


@router.put("/clusters/{cluster_id}/namespaces/{namespace}/quota")
async def set_quota(
    cluster_id: str, namespace: str, body: SetQuotaRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: ResourceQuotaService = Depends(get_resource_quota_service),
):
    return to_dict(await service.set_quota(tenant_id, cluster_id, namespace, **body.model_dump()))


class ApplyResourceRequest(BaseModel):
    namespace: str
    kind: str
    name: str
    spec: dict | None = None
    replicas: int | None = None


@router.post("/clusters/{cluster_id}/resources")
async def apply_resource(
    cluster_id: str, body: ApplyResourceRequest, tenant_id: str = Depends(get_current_tenant_id), service: K8sResourceService = Depends(get_k8s_resource_service)
):
    return to_dict(await service.apply_resource(tenant_id, cluster_id, **body.model_dump()))


@router.get("/clusters/{cluster_id}/resources")
async def list_resources(
    cluster_id: str, namespace: str, tenant_id: str = Depends(get_current_tenant_id), service: K8sResourceService = Depends(get_k8s_resource_service)
):
    return to_dict_list(await service.list_for_namespace(tenant_id, cluster_id, namespace))


class ScaleResourceRequest(BaseModel):
    replicas: int


@router.post("/resources/{resource_id}/scale")
async def scale_resource(resource_id: str, body: ScaleResourceRequest, tenant_id: str = Depends(get_current_tenant_id), service: K8sResourceService = Depends(get_k8s_resource_service)):
    return to_dict(await service.scale_resource(tenant_id, resource_id, **body.model_dump()))


@router.delete("/resources/{resource_id}", status_code=204)
async def delete_resource(resource_id: str, tenant_id: str = Depends(get_current_tenant_id), service: K8sResourceService = Depends(get_k8s_resource_service)):
    await service.delete_resource(tenant_id, resource_id)


class CreateAutoscalerRequest(BaseModel):
    namespace: str
    target_resource_name: str
    kind: str = "hpa"
    min_replicas: int | None = None
    max_replicas: int | None = None
    target_cpu_percent: int | None = None
    target_memory_percent: int | None = None


@router.post("/clusters/{cluster_id}/autoscalers", status_code=201)
async def create_autoscaler(
    cluster_id: str, body: CreateAutoscalerRequest, tenant_id: str = Depends(get_current_tenant_id), service: AutoscalerService = Depends(get_k8s_autoscaler_service)
):
    return to_dict(await service.create_autoscaler(tenant_id, cluster_id, **body.model_dump()))


@router.get("/clusters/{cluster_id}/autoscalers")
async def list_autoscalers(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AutoscalerService = Depends(get_k8s_autoscaler_service)):
    return to_dict_list(await service.list_for_cluster(tenant_id, cluster_id))
