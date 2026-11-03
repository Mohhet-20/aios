"""Read-only observability metrics: auth rates, session activity,
permission usage, API key usage, org growth, workspace activity, and
security overview."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from identity_platform.dependencies.dependencies import get_observability_metrics_service
from identity_platform.observability.metrics_service import ObservabilityMetricsService

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/auth")
async def auth_metrics(since: datetime | None = None, service: ObservabilityMetricsService = Depends(get_observability_metrics_service)):
    return await service.auth_metrics(since=since)


@router.get("/sessions")
async def session_metrics(service: ObservabilityMetricsService = Depends(get_observability_metrics_service)):
    return await service.session_metrics()


@router.get("/organizations/{organization_id}/api-keys")
async def api_key_usage(organization_id: str, service: ObservabilityMetricsService = Depends(get_observability_metrics_service)):
    return await service.api_key_usage(organization_id)


@router.get("/organization-growth")
async def organization_growth(since: datetime, service: ObservabilityMetricsService = Depends(get_observability_metrics_service)):
    return await service.organization_growth(since=since)


@router.get("/organizations/{organization_id}/workspace-activity")
async def workspace_activity(organization_id: str, service: ObservabilityMetricsService = Depends(get_observability_metrics_service)):
    return await service.workspace_activity(organization_id)


@router.get("/organizations/{organization_id}/permission-usage")
async def permission_usage(organization_id: str, service: ObservabilityMetricsService = Depends(get_observability_metrics_service)):
    return await service.permission_usage(organization_id)


@router.get("/organizations/{organization_id}/security-overview")
async def security_overview(organization_id: str, service: ObservabilityMetricsService = Depends(get_observability_metrics_service)):
    return await service.security_overview(organization_id)
