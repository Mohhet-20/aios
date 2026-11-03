"""Unversioned health checks for infra/load-balancer probes.

`/health` is kept for backward compatibility with existing callers/tests.
`/health/live` and `/health/ready` are the Phase-24 production-hardening
addition: liveness never touches the database (a slow/unreachable DB must
never fail liveness, which would trigger a pointless pod restart), while
readiness runs a real `SELECT 1` and returns 503 when the database is
unreachable, so a load balancer stops routing traffic to a broken pod
instead of learning about it from failed requests."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from identity_platform.dependencies.dependencies import get_session
from identity_platform.core.health_check import build_readiness_report

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/live")
async def liveness() -> dict:
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(response: Response, session: AsyncSession = Depends(get_session)) -> dict:
    report = await build_readiness_report(session)
    response.status_code = 200 if report.healthy else 503
    return {
        "status": "ready" if report.healthy else "not_ready",
        "components": [
            {"name": c.name, "healthy": c.healthy, "latency_ms": c.latency_ms, "detail": c.detail}
            for c in report.components
        ],
    }
