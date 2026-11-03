"""Minimal interval-based scheduler for recurring background work (e.g. a
nightly dataset refresh, an hourly notification digest). Cron-expression
scheduling is deliberately out of scope here — `APScheduler` is the natural
upgrade if/when real cron semantics are needed; this class exists to prove
out the "Scheduling" requirement's interface without pulling in a dependency
this project doesn't yet need.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.logging.setup import get_logger

logger = get_logger(__name__)


class IntervalScheduler:
    def __init__(self) -> None:
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def schedule(self, name: str, interval_seconds: float, fn: Callable[[], Awaitable[None]]) -> None:
        async def _loop():
            while self._running:
                await asyncio.sleep(interval_seconds)
                if not self._running:
                    break
                try:
                    await fn()
                except Exception as exc:  # noqa: BLE001
                    logger.error("scheduled_job_failed", job_name=name, error=str(exc))

        self._pending = getattr(self, "_pending", [])
        self._pending.append((name, _loop))

    async def start(self) -> None:
        self._running = True
        for name, loop_fn in getattr(self, "_pending", []):
            self._tasks.append(asyncio.create_task(loop_fn()))
            logger.info("scheduled_job_started", job_name=name)

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)


scheduler = IntervalScheduler()
