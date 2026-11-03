"""Observability & Release Analytics: deployment metrics and version
adoption snapshots."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.analytics.analytics_service import AdoptionSnapshotService, DeploymentMetricService
from release_platform.dependencies.dependencies import (
    get_adoption_snapshot_service,
    get_current_tenant_id,
    get_deployment_metric_service,
)
from release_platform.release_api.serialization import to_dict

router = APIRouter(prefix="/analytics", tags=["analytics"])
adoption_router = APIRouter(prefix="/adoption-snapshots", tags=["analytics"])


class RecordMetricRequest(BaseModel):
    metric_type: str
    value: float = 0.0
    deployment_id: str | None = None


@router.post("/metrics", status_code=201)
async def record_metric(
    body: RecordMetricRequest, tenant_id: str = Depends(get_current_tenant_id), service: DeploymentMetricService = Depends(get_deployment_metric_service),
):
    return to_dict(await service.record_metric(tenant_id, **body.model_dump()))


@router.get("/deployment-success-rate")
async def deployment_success_rate(
    tenant_id: str = Depends(get_current_tenant_id), service: DeploymentMetricService = Depends(get_deployment_metric_service),
):
    return {"rate": await service.deployment_success_rate(tenant_id)}


@router.get("/rollback-frequency")
async def rollback_frequency(
    tenant_id: str = Depends(get_current_tenant_id), service: DeploymentMetricService = Depends(get_deployment_metric_service),
):
    return {"frequency": await service.rollback_frequency(tenant_id)}


@router.get("/average-deployment-duration")
async def average_deployment_duration(
    tenant_id: str = Depends(get_current_tenant_id), service: DeploymentMetricService = Depends(get_deployment_metric_service),
):
    return {"average_seconds": await service.average_deployment_duration(tenant_id)}


@router.get("/failed-release-count")
async def failed_release_count(
    tenant_id: str = Depends(get_current_tenant_id), service: DeploymentMetricService = Depends(get_deployment_metric_service),
):
    return {"count": await service.failed_release_count(tenant_id)}


class RecordSnapshotRequest(BaseModel):
    version: str
    adoption_pct: float


@adoption_router.post("", status_code=201)
async def record_snapshot(
    body: RecordSnapshotRequest, tenant_id: str = Depends(get_current_tenant_id), service: AdoptionSnapshotService = Depends(get_adoption_snapshot_service),
):
    return to_dict(await service.record_snapshot(tenant_id, **body.model_dump()))


@adoption_router.get("/{version}")
async def get_latest_adoption(
    version: str, tenant_id: str = Depends(get_current_tenant_id), service: AdoptionSnapshotService = Depends(get_adoption_snapshot_service),
):
    return {"version": version, "adoption_pct": await service.latest_adoption(tenant_id, version)}
