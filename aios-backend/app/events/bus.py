"""In-process async event bus.

This is the "Future Event Bus integration" seam called out in the original architecture:
`publish()`/`subscribe()` are the only two operations any caller needs, so
swapping this implementation for a real broker (Kafka, NATS, Redis Streams)
later touches only this file — every publisher and subscriber in the
codebase is written against the interface, not the in-memory mechanism.

Handlers run as fire-and-forget asyncio tasks so a slow subscriber (e.g. a
notification handler) never blocks the request that published the event.
Failures in one handler are logged and do not affect other subscribers or
the publisher.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.domain.events.base import DomainEvent
from app.logging.setup import get_logger

logger = get_logger(__name__)

E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)
        self._background_tasks: set[asyncio.Task] = set()

    def subscribe(self, event_type: type[E], handler: Handler) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._subscribers.get(type(event), [])
        logger.debug(
            "event_published",
            event_name=event.event_name,
            event_id=event.event_id,
            subscriber_count=len(handlers),
        )
        for handler in handlers:
            task = asyncio.create_task(self._run_handler(handler, event))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _run_handler(self, handler: Handler, event: DomainEvent) -> None:
        try:
            await handler(event)
        except Exception as exc:  # noqa: BLE001 - a handler failure must never crash the publisher
            logger.error("event_handler_failed", event_name=event.event_name, error=str(exc), exc_info=True)

    async def publish_and_wait(self, event: DomainEvent) -> None:
        """Synchronous-style publish used by tests that need handlers to
        have run before asserting on their side effects."""
        handlers = self._subscribers.get(type(event), [])
        for handler in handlers:
            await handler(event)


event_bus = EventBus()
