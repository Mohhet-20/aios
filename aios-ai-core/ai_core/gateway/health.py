from __future__ import annotations

from fastapi import APIRouter, Response

from ai_core.observability.metrics import render_metrics

health_router = APIRouter()
metrics_router = APIRouter()


@health_router.get("/health/live")
async def liveness() -> dict:
    return {"status": "ok"}


@health_router.get("/health/ready")
async def readiness() -> dict:
    # The AI Core has no required database of its own; readiness here means
    # "the process is up and settings loaded," which is checked implicitly
    # by this handler running at all. Provider health is a separate,
    # per-provider concern — see GET /v1/models/{provider}/{name}/health.
    return {"status": "ready"}


@metrics_router.get("/metrics")
async def metrics() -> Response:
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
