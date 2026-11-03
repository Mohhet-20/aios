"""Infra Observability API: generic metrics, deployment success-rate
aggregation, and cluster health checks."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.dependencies.dependencies import get_cluster_health_service, get_current_tenant_id, get_infra_metric_service
from infra_platform.infra_api.serialization import to_dict, to_dict_list
from infra_platform.observability.observability_service import ClusterHealthService, InfraMetricService

router = APIRouter(prefix="/observability", tags=["observability"])


class RecordMetricRequest(BaseModel):
    metric_name: str
    value: float
    unit: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    tags: dict | None = None


@router.post("/metrics", status_code=201)
async def record_metric(body: RecordMetricRequest, tenant_id: str = Depends(get_current_tenant_id), service: InfraMetricService = Depends(get_infra_metric_service)):
    return to_dict(await service.record_metric(tenant_id, **body.model_dump()))


@router.get("/metrics")
async def list_recent_metrics(metric_name: str | None = None, limit: int = 200, tenant_id: str = Depends(get_current_tenant_id), service: InfraMetricService = Depends(get_infra_metric_service)):
    return to_dict_list(await service.list_recent(tenant_id, metric_name=metric_name, limit=limit))


@router.post("/metrics/prune")
async def prune_metrics(tenant_id: str = Depends(get_current_tenant_id), service: InfraMetricService = Depends(get_infra_metric_service)):
    return {"pruned": await service.prune_old_metrics(tenant_id)}


@router.get("/deployments/success-rate")
async def deployment_success_rate(tenant_id: str = Depends(get_current_tenant_id), service: InfraMetricService = Depends(get_infra_metric_service)):
    return await service.deployment_success_rate(tenant_id)


class RecordHealthCheckRequest(BaseModel):
    status: str
    details: dict | None = None


@router.post("/clusters/{cluster_id}/health-checks", status_code=201)
async def record_health_check(cluster_id: str, body: RecordHealthCheckRequest, tenant_id: str = Depends(get_current_tenant_id), service: ClusterHealthService = Depends(get_cluster_health_service)):
    return to_dict(await service.record_health_check(tenant_id, cluster_id, **body.model_dump()))


@router.get("/clusters/{cluster_id}/health-checks")
async def list_health_checks(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ClusterHealthService = Depends(get_cluster_health_service)):
    return to_dict_list(await service.list_for_cluster(tenant_id, cluster_id))


@router.get("/clusters/{cluster_id}/health-checks/latest")
async def latest_health_check(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ClusterHealthService = Depends(get_cluster_health_service)):
    return to_dict(await service.latest_for_cluster(tenant_id, cluster_id))
