"""Aggregates every v1 router (health is mounted separately at the
app root, not under /api/v1) into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from analytics_platform.an_api.v1 import (
    analytics,
    dashboards,
    forecasts,
    kpis,
    observability,
    recommendations,
    reports,
    security,
    warehouse,
)

api_router = APIRouter()

api_router.include_router(warehouse.router)
api_router.include_router(warehouse.events_router)

api_router.include_router(analytics.router)

api_router.include_router(kpis.router)
api_router.include_router(kpis.snapshots_router)

api_router.include_router(reports.router)
api_router.include_router(reports.runs_router)

api_router.include_router(forecasts.router)

api_router.include_router(recommendations.router)

api_router.include_router(dashboards.router)

api_router.include_router(security.router)
api_router.include_router(security.rls_router)
api_router.include_router(security.cls_router)
api_router.include_router(security.audit_router)
api_router.include_router(security.lineage_router)

api_router.include_router(observability.router)
api_router.include_router(observability.query_perf_router)
api_router.include_router(observability.accuracy_router)
api_router.include_router(observability.recommendation_analytics_router)
