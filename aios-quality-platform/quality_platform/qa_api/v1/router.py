"""Aggregates every v1 router (health is mounted separately at the
app root, not under /api/v1) into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from quality_platform.qa_api.v1 import (
    ai_quality,
    certification,
    chaos,
    failure_analysis,
    observability,
    performance,
    quality_gates,
    reliability,
    security_testing,
    testing,
    validation,
)

api_router = APIRouter()

api_router.include_router(testing.router)
api_router.include_router(testing.runs_router)

api_router.include_router(ai_quality.router)

api_router.include_router(performance.router)

api_router.include_router(chaos.router)

api_router.include_router(security_testing.router)

api_router.include_router(validation.router)
api_router.include_router(validation.workflow_router)

api_router.include_router(reliability.router)
api_router.include_router(reliability.snapshots_router)

api_router.include_router(quality_gates.router)
api_router.include_router(quality_gates.coverage_router)

api_router.include_router(failure_analysis.router)
api_router.include_router(failure_analysis.risk_router)

api_router.include_router(certification.router)

api_router.include_router(observability.router)
