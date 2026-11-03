"""Abstract background task queue.

`enqueue()` is the only method callers (services) need. The concrete
implementation (`InProcessWorkerPool`, an asyncio task queue) is correct for
local dev, tests, and a single-instance deployment; swapping to Celery/RQ/
Arq backed by Redis for a multi-instance production deployment means
implementing this same `TaskQueue` protocol and changing one DI binding in
`app.dependencies.service_dependencies` — no service code changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.clock import utc_now
from app.domain.value_objects.enums import JobStatus


@dataclass
class JobRecord:
    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = ""
    status: JobStatus = JobStatus.QUEUED
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=lambda: utc_now())
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: Any = None


JobFn = Callable[..., Awaitable[Any]]


class TaskQueue(ABC):
    @abstractmethod
    async def enqueue(self, name: str, fn: JobFn, *args, max_attempts: int = 3, **kwargs) -> JobRecord: ...

    @abstractmethod
    def get_job(self, job_id: str) -> JobRecord | None: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...
