"""Asyncio-based in-process worker pool implementing `TaskQueue`.

Supports retries with exponential backoff (via `tenacity`) and keeps
`JobRecord`s in memory so `GET /api/v1/workers/jobs/{id}` (see
`monitoring_router`) can report job status without a separate datastore.
This is explicitly the dev/single-instance implementation described in
`task_queue.py`'s docstring — see that file for the production swap-out
plan.
"""

from __future__ import annotations

import asyncio

from tenacity import retry, stop_after_attempt, wait_exponential

from app.clock import utc_now
from app.domain.value_objects.enums import JobStatus
from app.logging.setup import get_logger
from app.workers.task_queue import JobFn, JobRecord, TaskQueue

logger = get_logger(__name__)


class InProcessWorkerPool(TaskQueue):
    def __init__(self, concurrency: int = 4):
        self._queue: asyncio.Queue[tuple[JobRecord, JobFn, tuple, dict]] = asyncio.Queue()
        self._jobs: dict[str, JobRecord] = {}
        self._concurrency = concurrency
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def enqueue(self, name: str, fn: JobFn, *args, max_attempts: int = 3, **kwargs) -> JobRecord:
        record = JobRecord(name=name, max_attempts=max_attempts)
        self._jobs[record.id] = record
        await self._queue.put((record, fn, args, kwargs))
        logger.info("job_enqueued", job_id=record.id, job_name=name)
        return record

    def get_job(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> list[JobRecord]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)[:limit]

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._workers = [asyncio.create_task(self._worker_loop(i)) for i in range(self._concurrency)]
        logger.info("worker_pool_started", concurrency=self._concurrency)

    async def stop(self) -> None:
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("worker_pool_stopped")

    async def _worker_loop(self, worker_index: int) -> None:
        while self._running:
            try:
                record, fn, args, kwargs = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            await self._execute_with_retry(record, fn, args, kwargs)

    async def _execute_with_retry(self, record: JobRecord, fn: JobFn, args: tuple, kwargs: dict) -> None:
        record.status = JobStatus.RUNNING
        record.started_at = utc_now()

        @retry(
            stop=stop_after_attempt(record.max_attempts),
            wait=wait_exponential(multiplier=0.5, max=8),
            reraise=True,
        )
        async def _run():
            record.attempts += 1
            return await fn(*args, **kwargs)

        try:
            record.result = await _run()
            record.status = JobStatus.SUCCEEDED
            logger.info("job_succeeded", job_id=record.id, job_name=record.name, attempts=record.attempts)
        except Exception as exc:  # noqa: BLE001
            record.status = JobStatus.FAILED
            record.error = str(exc)
            logger.error(
                "job_failed", job_id=record.id, job_name=record.name, attempts=record.attempts, error=str(exc)
            )
        finally:
            record.completed_at = utc_now()


worker_pool = InProcessWorkerPool()
