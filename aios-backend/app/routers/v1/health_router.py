from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.monitoring.health import build_readiness_report

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def liveness():
    """Never touches the database — a slow/unreachable DB must not fail
    liveness (which would trigger a pointless pod restart in k8s)."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness(response: Response, session: AsyncSession = Depends(get_db_session)):
    report = await build_readiness_report(session)
    response.status_code = 200 if report.healthy else 503
    return {
        "status": "ready" if report.healthy else "not_ready",
        "components": [
            {"name": c.name, "healthy": c.healthy, "latency_ms": c.latency_ms, "detail": c.detail}
            for c in report.components
        ],
    }
