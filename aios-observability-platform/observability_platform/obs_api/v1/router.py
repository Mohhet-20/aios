"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from observability_platform.obs_api.v1 import (
    alerts,
    analytics,
    capacity,
    dashboards,
    governance,
    incidents,
    logs,
    metrics,
    monitoring,
    reporting,
    topology,
    tracing,
)

api_router = APIRouter()
api_router.include_router(logs.router)
api_router.include_router(metrics.router)
api_router.include_router(tracing.router)
api_router.include_router(monitoring.components_router)
api_router.include_router(monitoring.health_router)
api_router.include_router(alerts.router)
api_router.include_router(alerts.maintenance_router)
api_router.include_router(alerts.channels_router)
api_router.include_router(incidents.router)
api_router.include_router(analytics.router)
api_router.include_router(capacity.router)
api_router.include_router(topology.router)
api_router.include_router(dashboards.router)
api_router.include_router(reporting.router)
api_router.include_router(governance.router)
