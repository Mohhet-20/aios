"""Aggregation & Analytics Engine: rollup computation, generic and
domain-locked (business/AI/financial/performance)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from analytics_platform.an_api.serialization import to_dict, to_dict_list
from analytics_platform.analytics.ai_analytics_service import AiAnalyticsService
from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.analytics.business_analytics_service import BusinessAnalyticsService
from analytics_platform.analytics.financial_analytics_service import FinancialAnalyticsService
from analytics_platform.analytics.performance_analytics_service import PerformanceAnalyticsService
from analytics_platform.dependencies.dependencies import (
    get_aggregation_engine,
    get_ai_analytics_service,
    get_business_analytics_service,
    get_current_tenant_id,
    get_financial_analytics_service,
    get_performance_analytics_service,
)

router = APIRouter(prefix="/rollups", tags=["analytics"])


class ComputeRollupRequest(BaseModel):
    metric_key: str
    domain: str
    period: str
    period_start: datetime
    period_end: datetime
    aggregation_type: str = "sum"


@router.post("", status_code=201)
async def compute_rollup(
    body: ComputeRollupRequest, tenant_id: str = Depends(get_current_tenant_id),
    engine: AggregationEngine = Depends(get_aggregation_engine),
):
    return to_dict(await engine.compute_rollup(tenant_id, body.metric_key, **body.model_dump(exclude={"metric_key"})))


@router.get("")
async def list_rollups(
    metric_key: str, domain: str | None = None, period: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id), engine: AggregationEngine = Depends(get_aggregation_engine),
):
    return to_dict_list(await engine.list_rollups(tenant_id, metric_key, domain=domain, period=period))


class DomainRollupRequest(BaseModel):
    metric_key: str
    period: str
    period_start: datetime
    period_end: datetime
    aggregation_type: str = "sum"


@router.post("/business", status_code=201)
async def compute_business_rollup(
    body: DomainRollupRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: BusinessAnalyticsService = Depends(get_business_analytics_service),
):
    return to_dict(await service.compute_rollup(tenant_id, **body.model_dump()))


@router.post("/ai", status_code=201)
async def compute_ai_rollup(
    body: DomainRollupRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: AiAnalyticsService = Depends(get_ai_analytics_service),
):
    return to_dict(await service.compute_rollup(tenant_id, **body.model_dump()))


@router.post("/financial", status_code=201)
async def compute_financial_rollup(
    body: DomainRollupRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: FinancialAnalyticsService = Depends(get_financial_analytics_service),
):
    return to_dict(await service.compute_rollup(tenant_id, **body.model_dump()))


@router.post("/performance", status_code=201)
async def compute_performance_rollup(
    body: DomainRollupRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PerformanceAnalyticsService = Depends(get_performance_analytics_service),
):
    return to_dict(await service.compute_rollup(tenant_id, **body.model_dump()))
