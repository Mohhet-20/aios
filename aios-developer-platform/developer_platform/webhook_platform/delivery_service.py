"""Webhook delivery orchestration: fan-out an event to every active,
matching subscription, attempt delivery through an injectable
`sender` (defaults to a real `httpx` POST), and retry failures with
linear backoff up to `webhook_max_retry_attempts` before marking a
delivery exhausted. `replay_delivery` never mutates a past delivery
row — it spawns a fresh one, keeping the delivery log an honest
append-only history of what was actually attempted and when."""
from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import httpx

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import NotFoundError, WebhookNotFoundError
from developer_platform.database.base import utcnow
from developer_platform.domain.enums import WebhookDeliveryStatus
from developer_platform.models.webhooks import WebhookDeliveryModel
from developer_platform.repositories.registry import RepositoryRegistry
from developer_platform.webhook_platform.mappers import apply_webhook_delivery_domain_to_model, webhook_delivery_to_domain
from developer_platform.webhook_platform.signing_service import WebhookSigningService
from developer_platform.webhook_platform.subscription_service import matches_event

SenderResult = tuple[bool, str | None]
Sender = Callable[[str, dict, str], SenderResult]


def default_sender(url: str, payload: dict, signature: str, *, timeout: float = 10.0) -> SenderResult:
    """Real HTTP delivery via `httpx`. Kept as a free function (not a
    method) so tests can pass a trivial stand-in without touching the
    network, and so a caller can swap in a queue-backed sender in
    production without subclassing anything."""
    try:
        response = httpx.post(url, json=payload, headers={"X-AIOS-Signature": signature}, timeout=timeout)
        if response.status_code < 400:
            return True, None
        return False, f"HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        return False, str(exc)


class WebhookDeliveryService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None, signer: WebhookSigningService | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.signer = signer or WebhookSigningService(settings=self.settings)

    async def dispatch_event(self, tenant_id: str, *, event_type: str, payload: dict) -> list[WebhookDeliveryModel]:
        created: list[WebhookDeliveryModel] = []
        for subscription in await self.repos.webhook_subscriptions.list_active(tenant_id):
            if not matches_event(subscription, event_type):
                continue
            delivery = WebhookDeliveryModel(
                tenant_id=tenant_id, subscription_id=subscription.id, event_type=event_type,
                payload=payload, status=WebhookDeliveryStatus.PENDING.value, attempt_count=0,
            )
            created.append(await self.repos.webhook_deliveries.add(delivery))
        return created

    async def attempt_delivery(
        self, tenant_id: str, delivery_id: str, *, secret: str, sender: Sender | None = None,
    ) -> WebhookDeliveryModel:
        sender = sender or default_sender
        delivery = await self._get_delivery_or_404(tenant_id, delivery_id)
        subscription = await self.repos.webhook_subscriptions.get_or_404(delivery.subscription_id)

        entity = webhook_delivery_to_domain(delivery)
        entity.start_delivery()
        apply_webhook_delivery_domain_to_model(entity, delivery)
        delivery.attempt_count += 1

        signature = self.signer.sign_payload(delivery.payload, secret)
        success, error = sender(subscription.target_url, delivery.payload, signature)

        entity = webhook_delivery_to_domain(delivery)
        if success:
            entity.succeed()
            apply_webhook_delivery_domain_to_model(entity, delivery)
            delivery.last_error = None
            delivery.next_attempt_at = None
        else:
            entity.fail()
            apply_webhook_delivery_domain_to_model(entity, delivery)
            delivery.last_error = error
            if delivery.attempt_count >= self.settings.webhook_max_retry_attempts:
                entity = webhook_delivery_to_domain(delivery)
                entity.exhaust()
                apply_webhook_delivery_domain_to_model(entity, delivery)
                delivery.next_attempt_at = None
            else:
                backoff = self.settings.webhook_retry_backoff_seconds * delivery.attempt_count
                delivery.next_attempt_at = utcnow() + timedelta(seconds=backoff)

        return await self.repos.webhook_deliveries.update(delivery)

    async def replay_delivery(self, tenant_id: str, delivery_id: str) -> WebhookDeliveryModel:
        original = await self._get_delivery_or_404(tenant_id, delivery_id)
        replay = WebhookDeliveryModel(
            tenant_id=tenant_id, subscription_id=original.subscription_id, event_type=original.event_type,
            payload=original.payload, status=WebhookDeliveryStatus.PENDING.value, attempt_count=0,
        )
        return await self.repos.webhook_deliveries.add(replay)

    async def list_due_for_retry(self, tenant_id: str):
        return await self.repos.webhook_deliveries.list_due_for_retry(tenant_id, before=utcnow())

    async def sweep_retries(
        self, tenant_id: str, *, secret_lookup: Callable[[str], str], sender: Sender | None = None,
    ) -> list[WebhookDeliveryModel]:
        """Failure-recovery sweep: re-attempts every delivery whose
        `next_attempt_at` has passed. `secret_lookup` maps a
        subscription's `secret_ref` to the real signing secret — in
        production this hits a secret manager; tests pass a plain dict
        lookup."""
        results: list[WebhookDeliveryModel] = []
        for delivery in await self.list_due_for_retry(tenant_id):
            subscription = await self.repos.webhook_subscriptions.get_or_404(delivery.subscription_id)
            secret = secret_lookup(subscription.secret_ref)
            results.append(await self.attempt_delivery(tenant_id, delivery.id, secret=secret, sender=sender))
        return results

    async def list_for_subscription(self, tenant_id: str, subscription_id: str) -> list[WebhookDeliveryModel]:
        return await self.repos.webhook_deliveries.list_for_subscription(tenant_id, subscription_id)

    async def _get_delivery_or_404(self, tenant_id: str, delivery_id: str) -> WebhookDeliveryModel:
        try:
            delivery = await self.repos.webhook_deliveries.get_or_404(delivery_id)
        except NotFoundError as exc:
            raise WebhookNotFoundError(f"Webhook delivery '{delivery_id}' not found") from exc
        if delivery.tenant_id != tenant_id:
            raise WebhookNotFoundError(f"Webhook delivery '{delivery_id}' not found for tenant '{tenant_id}'")
        return delivery
