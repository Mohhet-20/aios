"""Security Observability & Analytics API: read-only aggregation
views over every other module."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from security_platform.analytics.security_analytics_service import SecurityAnalyticsService
from security_platform.dependencies.dependencies import get_current_tenant_id, get_security_analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/threat-trends")
async def threat_trends(since_hours: int = 24, tenant_id: str = Depends(get_current_tenant_id), service: SecurityAnalyticsService = Depends(get_security_analytics_service)):
    return await service.threat_trends(tenant_id, since_hours=since_hours)


@router.get("/policy-violations")
async def policy_violation_summary(tenant_id: str = Depends(get_current_tenant_id), service: SecurityAnalyticsService = Depends(get_security_analytics_service)):
    return await service.policy_violation_summary(tenant_id)


@router.get("/risk-distribution/{entity_type}")
async def risk_score_distribution(entity_type: str, limit: int = 500, tenant_id: str = Depends(get_current_tenant_id), service: SecurityAnalyticsService = Depends(get_security_analytics_service)):
    return await service.risk_score_distribution(tenant_id, entity_type, limit=limit)


@router.get("/incidents")
async def security_incident_summary(tenant_id: str = Depends(get_current_tenant_id), service: SecurityAnalyticsService = Depends(get_security_analytics_service)):
    return await service.security_incident_summary(tenant_id)


@router.get("/compliance-status")
async def compliance_status(tenant_id: str = Depends(get_current_tenant_id), service: SecurityAnalyticsService = Depends(get_security_analytics_service)):
    return await service.compliance_status(tenant_id)


@router.get("/secrets-usage")
async def secrets_usage_summary(since_hours: int = 24, tenant_id: str = Depends(get_current_tenant_id), service: SecurityAnalyticsService = Depends(get_security_analytics_service)):
    return await service.secrets_usage_summary(tenant_id, since_hours=since_hours)


@router.get("/encryption-status")
async def encryption_status(tenant_id: str = Depends(get_current_tenant_id), service: SecurityAnalyticsService = Depends(get_security_analytics_service)):
    return await service.encryption_status(tenant_id)


@router.get("/governance-metrics")
async def governance_metrics(tenant_id: str = Depends(get_current_tenant_id), service: SecurityAnalyticsService = Depends(get_security_analytics_service)):
    return await service.governance_metrics(tenant_id)
