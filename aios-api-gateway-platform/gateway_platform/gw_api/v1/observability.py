"""Observability, Analytics & Topology: raw metrics, dependency
topology, periodic analytics snapshots."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import (
    get_analytics_snapshot_service,
    get_current_tenant_id,
    get_dependency_topology_service,
    get_gateway_metrics_service,
)
from gateway_platform.gw_api.serialization import to_dict, to_dict_list
from gateway_platform.observability.analytics_service import AnalyticsSnapshotService
from gateway_platform.observability.metrics_service import GatewayMetricsService
from gateway_platform.observability.topology_service import DependencyTopologyService

router = APIRouter(prefix="/observability/metrics", tags=["observability"])


class RecordMetricRequest(BaseModel):
    metric_type: str
    value: float
    route_id: str | None = None
    service_id: str | None = None


@router.post("", status_code=201)
async def record_metric(
    body: RecordMetricRequest, tenant_id: str = Depends(get_current_tenant_id), service: GatewayMetricsService = Depends(get_gateway_metrics_service),
):
    return to_dict(await service.record_metric(tenant_id, **body.model_dump()))


@router.get("")
async def list_metrics(
    metric_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: GatewayMetricsService = Depends(get_gateway_metrics_service),
):
    return to_dict_list(await service.list_recent(tenant_id, metric_type=metric_type))


@router.get("/error-rate")
async def get_error_rate(tenant_id: str = Depends(get_current_tenant_id), service: GatewayMetricsService = Depends(get_gateway_metrics_service)):
    return {"error_rate": await service.error_rate(tenant_id)}


topology_router = APIRouter(prefix="/observability/topology", tags=["observability"])


class RecordCallRequest(BaseModel):
    from_service: str
    to_service: str
    latency_ms: float


@topology_router.post("", status_code=201)
async def record_call(
    body: RecordCallRequest, tenant_id: str = Depends(get_current_tenant_id), service: DependencyTopologyService = Depends(get_dependency_topology_service),
):
    return to_dict(await service.record_call(tenant_id, **body.model_dump()))


@topology_router.get("")
async def get_graph(tenant_id: str = Depends(get_current_tenant_id), service: DependencyTopologyService = Depends(get_dependency_topology_service)):
    return to_dict_list(await service.graph(tenant_id))


analytics_router = APIRouter(prefix="/observability/analytics", tags=["observability"])


class CreateSnapshotRequest(BaseModel):
    snapshot_type: str
    period_start: datetime
    period_end: datetime
    data: dict


@analytics_router.post("", status_code=201)
async def create_snapshot(
    body: CreateSnapshotRequest, tenant_id: str = Depends(get_current_tenant_id), service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service),
):
    return to_dict(await service.create_snapshot(tenant_id, **body.model_dump()))


@analytics_router.get("/{snapshot_type}")
async def list_snapshots(
    snapshot_type: str, tenant_id: str = Depends(get_current_tenant_id), service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service),
):
    return to_dict_list(await service.list_by_type(tenant_id, snapshot_type))


@analytics_router.get("/{snapshot_type}/latest")
async def get_latest_snapshot(
    snapshot_type: str, tenant_id: str = Depends(get_current_tenant_id), service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service),
):
    return to_dict(await service.latest(tenant_id, snapshot_type))
