"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from eval_platform.eval_api.v1 import (
    alerting,
    analytics,
    benchmarks,
    datasets,
    evaluations,
    governance,
    hallucination,
    metrics,
    observability,
    runs,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(workspaces.router)
api_router.include_router(evaluations.router)
api_router.include_router(datasets.router)
api_router.include_router(runs.router)
api_router.include_router(benchmarks.router)
api_router.include_router(metrics.router)
api_router.include_router(hallucination.router)
api_router.include_router(observability.router)
api_router.include_router(alerting.router)
api_router.include_router(analytics.router)
api_router.include_router(governance.router)
