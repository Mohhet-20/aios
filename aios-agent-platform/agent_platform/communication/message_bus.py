"""In-process async event bus: the "event-driven messaging" and
"streaming messages" primitive every other communication pattern
(direct, broadcast, handoff, status update) publishes through, so a
future real subscriber (a websocket layer, a webhook dispatcher) has one
place to plug in instead of touching every call site.

Deliberately in-process and swappable — `EventBus` is the seam a real
message broker (Kafka/Redis/NATS) would sit behind in a horizontally-
scaled deployment; nothing above this layer depends on it being
in-process.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable

Handler = Callable[[dict], Awaitable[None] | None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        if handler in self._subscribers.get(event_type, []):
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, payload: dict) -> None:
        handlers = list(self._subscribers.get(event_type, [])) + list(self._subscribers.get("*", []))
        for handler in handlers:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                await result
