"""Health check aggregator. `/health/live` answers "is the process up"
(never touches the database — used for k8s liveness probes so a slow DB
never causes a needless pod restart). `/health/ready` answers "can this
instance serve traffic" (checks the DB connection — used for k8s readiness
probes / load balancer health checks).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ComponentHealth:
    name: str
    healthy: bool
    latency_ms: float | None = None
    detail: str | None = None


@dataclass
class HealthReport:
    healthy: bool
    components: list[ComponentHealth] = field(default_factory=list)


async def check_database(session: AsyncSession) -> ComponentHealth:
    start = time.perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        return ComponentHealth("database", True, round((time.perf_counter() - start) * 1000, 2))
    except Exception as exc:  # noqa: BLE001
        return ComponentHealth("database", False, detail=str(exc))


async def build_readiness_report(session: AsyncSession) -> HealthReport:
    components = [await check_database(session)]
    return HealthReport(healthy=all(c.healthy for c in components), components=components)
