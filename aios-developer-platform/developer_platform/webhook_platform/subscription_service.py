"""Webhook subscription management: register a target URL against a
filtered set of event types, with a signing secret generated once at
creation and never persisted in the clear (only an opaque
`SecretReferenceModel` pointer lives on the subscription row) — the
same "own the pointer, not the data" posture used for API keys and CLI
sessions in this platform."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from developer_platform.core.exceptions import NotFoundError, WebhookNotFoundError
from developer_platform.domain.enums import SecretReferenceType
from developer_platform.models.security import SecretReferenceModel
from developer_platform.models.webhooks import WebhookSubscriptionModel
from developer_platform.repositories.registry import RepositoryRegistry
from developer_platform.security.tokens import generate_raw_token


@dataclass
class WebhookSubscriptionResult:
    subscription: WebhookSubscriptionModel
    raw_secret: str


def matches_event(subscription: WebhookSubscriptionModel, event_type: str) -> bool:
    return "*" in subscription.event_types or event_type in subscription.event_types


class WebhookSubscriptionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_subscription(
        self, tenant_id: str, *, target_url: str, event_types: list[str],
    ) -> WebhookSubscriptionResult:
        raw_secret = generate_raw_token()
        secret_ref = SecretReferenceModel(
            tenant_id=tenant_id, name=f"webhook-secret-{uuid.uuid4().hex[:8]}",
            reference_type=SecretReferenceType.WEBHOOK_SECRET.value,
            material_ref=f"vault://webhook-secrets/{uuid.uuid4().hex}",
        )
        secret_ref = await self.repos.secret_references.add(secret_ref)

        subscription = WebhookSubscriptionModel(
            tenant_id=tenant_id, target_url=target_url, secret_ref=secret_ref.id,
            event_types=event_types, is_active=True,
        )
        subscription = await self.repos.webhook_subscriptions.add(subscription)
        return WebhookSubscriptionResult(subscription=subscription, raw_secret=raw_secret)

    async def deactivate(self, subscription_id: str) -> WebhookSubscriptionModel:
        subscription = await self._get_or_404(subscription_id)
        subscription.is_active = False
        return await self.repos.webhook_subscriptions.update(subscription)

    async def reactivate(self, subscription_id: str) -> WebhookSubscriptionModel:
        subscription = await self._get_or_404(subscription_id)
        subscription.is_active = True
        return await self.repos.webhook_subscriptions.update(subscription)

    async def update_filters(self, subscription_id: str, event_types: list[str]) -> WebhookSubscriptionModel:
        subscription = await self._get_or_404(subscription_id)
        subscription.event_types = event_types
        return await self.repos.webhook_subscriptions.update(subscription)

    async def list_active(self, tenant_id: str) -> list[WebhookSubscriptionModel]:
        return await self.repos.webhook_subscriptions.list_active(tenant_id)

    async def list_for_tenant(self, tenant_id: str) -> list[WebhookSubscriptionModel]:
        return await self.repos.webhook_subscriptions.list_for_tenant(tenant_id)

    async def _get_or_404(self, subscription_id: str) -> WebhookSubscriptionModel:
        try:
            return await self.repos.webhook_subscriptions.get_or_404(subscription_id)
        except NotFoundError as exc:
            raise WebhookNotFoundError(f"Webhook subscription '{subscription_id}' not found") from exc
