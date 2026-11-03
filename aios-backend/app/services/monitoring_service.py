"""MonitoringService — aggregates health + background-job status for the
Monitoring/Observability API surface. Distinct from
`app.monitoring.metrics`/`app.monitoring.health` (infrastructure-level
collectors) — this service is the application-layer facade routers call,
matching the pattern every other domain follows (routers depend on
services, not on infrastructure modules directly).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.monitoring.health import HealthReport, build_readiness_report
from app.workers.in_process_worker import InProcessWorkerPool
from app.workers.task_queue import JobRecord


class MonitoringService:
    def __init__(self, task_queue: InProcessWorkerPool):
        self.task_queue = task_queue

    async def readiness(self, session: AsyncSession) -> HealthReport:
        return await build_readiness_report(session)

    def list_jobs(self, limit: int = 50) -> list[JobRecord]:
        return self.task_queue.list_jobs(limit)

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.task_queue.get_job(job_id)
