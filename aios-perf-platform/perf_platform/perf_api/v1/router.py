"""Aggregates every v1 router (health is mounted separately at the
app root, not under /api/v1) into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from perf_platform.perf_api.v1 import cache, cost, observability, optimization, routing, scalability

api_router = APIRouter()

api_router.include_router(cache.router)

api_router.include_router(routing.router)

api_router.include_router(cost.router)
api_router.include_router(cost.budgets_router)

api_router.include_router(optimization.router)

api_router.include_router(observability.router)
api_router.include_router(observability.benchmarks_router)

api_router.include_router(scalability.router)
