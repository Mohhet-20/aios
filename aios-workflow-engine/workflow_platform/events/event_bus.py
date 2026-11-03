"""EventBus: the platform's in-process pub/sub substrate. Every workflow/
node/agent/memory/tool/external occurrence gets `publish()`ed here, which
(1) durably records it as an `EventModel` row — the append-only event
log every other subsystem (Observability, Approval escalation, a future
Analytics rollup) can read from independent of who happened to be
subscribed at the time — then (2) fans it out to whatever's currently
subscribed: an in-process Python callable (`SubscriptionTargetType.
INTERNAL_HANDLER`, dispatched by `handler_key` through an injectable
registry, the same pattern `CustomHandler`/`DatabaseQueryHandler` use) or
a real outbound HTTP delivery (`SubscriptionTargetType.WEBHOOK`, recorded
as its own `WebhookDeliveryModel` row so a failed delivery can be
retried without re-publishing the event).

Shares one `AsyncSession` with whatever else is using the same
`RepositoryRegistry` (typically the `ExecutionEngine`), so every
repository touch here is guarded by the same `asyncio.Lock` the engine
uses — pass the engine's `_session_lock` in via the `lock` constructor
argument when wiring the two together; a fresh, unshared lock is created
automatically for standalone use (tests, a dedicated event-consumer
process with its own session)."""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

import httpx

from workflow_platform.domain.enums import SubscriptionTargetType, WebhookDeliveryStatus
from workflow_platform.models.events import EventModel, SubscriptionModel, WebhookDeliveryModel
from workflow_platform.repositories.registry import RepositoryRegistry

InternalHandler = Callable[[EventModel], Awaitable[None]]


class EventBus:
    def __init__(
        self,
        repos: RepositoryRegistry,
        *,
        internal_handlers: dict[str, InternalHandler] | None = None,
        http_client: httpx.AsyncClient | None = None,
        lock: asyncio.Lock | None = None,
    ):
        self.repos = repos
        self._internal_handlers: dict[str, InternalHandler] = dict(internal_handlers or {})
        self._http_client = http_client
        self._lock = lock or asyncio.Lock()

    def register_handler(self, handler_key: str, fn: InternalHandler) -> None:
        self._internal_handlers[handler_key] = fn

    async def publish(
        self, *, event_type: str, workspace_id: str, source_type: str, source_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventModel:
        async with self._lock:
            event = await self.repos.events.add(EventModel(
                workspace_id=workspace_id, event_type=event_type, source_type=source_type,
                source_id=source_id, payload=payload or {},
            ))
            subscriptions = await self.repos.subscriptions.list_for_event_type(workspace_id, event_type)

            webhook_deliveries: list[tuple[WebhookDeliveryModel, SubscriptionModel]] = []
            internal_targets: list[SubscriptionModel] = []
            for sub in subscriptions:
                if sub.target_type == SubscriptionTargetType.WEBHOOK.value:
                    delivery = await self.repos.webhook_deliveries.add(WebhookDeliveryModel(
                        subscription_id=sub.id, event_id=event.id, status=WebhookDeliveryStatus.PENDING.value,
                    ))
                    webhook_deliveries.append((delivery, sub))
                elif sub.target_type == SubscriptionTargetType.INTERNAL_HANDLER.value:
                    internal_targets.append(sub)

        # actual I/O (HTTP delivery, arbitrary internal handler code) runs
        # outside the lock so it can't block other repos consumers; each
        # result write-back re-acquires the lock around just that write.
        for delivery, sub in webhook_deliveries:
            await self._deliver_webhook(delivery, sub, event)
        for sub in internal_targets:
            await self._call_internal_handler(sub, event)

        return event

    async def _deliver_webhook(self, delivery: WebhookDeliveryModel, sub: SubscriptionModel, event: EventModel) -> WebhookDeliveryModel:
        url = sub.target_config.get("url")
        headers = sub.target_config.get("headers")
        body = {
            "event_id": event.id, "event_type": event.event_type, "workspace_id": event.workspace_id,
            "source_type": event.source_type, "source_id": event.source_id, "payload": event.payload,
        }
        status = WebhookDeliveryStatus.FAILED.value
        status_code: int | None = None
        error_message: str | None = None
        try:
            if self._http_client is not None:
                response = await self._http_client.post(url, json=body, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(url, json=body, headers=headers)
            status_code = response.status_code
            status = WebhookDeliveryStatus.DELIVERED.value if response.is_success else WebhookDeliveryStatus.FAILED.value
        except Exception as exc:  # noqa: BLE001 — a delivery failure must never raise into the publisher
            error_message = str(exc)[:500]

        async with self._lock:
            delivery.attempt_count += 1
            delivery.status = status
            delivery.response_status_code = status_code
            delivery.error_message = error_message
            if status == WebhookDeliveryStatus.DELIVERED.value:
                from workflow_platform.database.base import utcnow
                delivery.delivered_at = utcnow()
            return await self.repos.webhook_deliveries.update(delivery)

    async def _call_internal_handler(self, sub: SubscriptionModel, event: EventModel) -> None:
        handler_key = sub.target_config.get("handler_key")
        fn = self._internal_handlers.get(handler_key)
        if fn is None:
            return  # unregistered handler_key: nothing to call, not a delivery failure
        await fn(event)

    # -- retry sweep (the actual periodic trigger is a Task 89 scheduler concern) ----

    async def retry_pending_webhook_deliveries(self, *, max_attempts: int = 5, limit: int = 100) -> int:
        async with self._lock:
            pending = await self.repos.webhook_deliveries.list_pending_retries(max_attempts=max_attempts, limit=limit)
            targets = []
            for delivery in pending:
                sub = await self.repos.subscriptions.get_or_404(delivery.subscription_id)
                event = await self.repos.events.get_or_404(delivery.event_id)
                targets.append((delivery, sub, event))

        delivered = 0
        for delivery, sub, event in targets:
            result = await self._deliver_webhook(delivery, sub, event)
            if result.status == WebhookDeliveryStatus.DELIVERED.value:
                delivered += 1
        return delivered
