"""Event subscriptions: binds a subscriber to a topic with an
optional filter (a plain dict of `payload` key/value equality checks
— deliberately simple, the same "own the pointer, not the parser"
posture as everywhere else in this platform that could otherwise grow
its own mini query language)."""
from __future__ import annotations

from gateway_platform.core.exceptions import SubscriptionNotFoundError
from gateway_platform.domain.enums import SubscriptionStatus
from gateway_platform.models.events import EventSubscriptionModel
from gateway_platform.repositories.registry import RepositoryRegistry


def matches_filter(payload: dict, event_filter: dict) -> bool:
    if not event_filter:
        return True
    return all(payload.get(key) == value for key, value in event_filter.items())


class EventSubscriptionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def subscribe(
        self, tenant_id: str, topic_id: str, *, subscriber: str, event_filter: dict | None = None,
    ) -> EventSubscriptionModel:
        subscription = EventSubscriptionModel(
            tenant_id=tenant_id, topic_id=topic_id, subscriber=subscriber,
            status=SubscriptionStatus.ACTIVE.value, event_filter=event_filter or {},
        )
        return await self.repos.event_subscriptions.add(subscription)

    async def pause(self, tenant_id: str, subscription_id: str) -> EventSubscriptionModel:
        subscription = await self._get_or_404(tenant_id, subscription_id)
        subscription.status = SubscriptionStatus.PAUSED.value
        return await self.repos.event_subscriptions.update(subscription)

    async def resume(self, tenant_id: str, subscription_id: str) -> EventSubscriptionModel:
        subscription = await self._get_or_404(tenant_id, subscription_id)
        subscription.status = SubscriptionStatus.ACTIVE.value
        return await self.repos.event_subscriptions.update(subscription)

    async def cancel(self, tenant_id: str, subscription_id: str) -> EventSubscriptionModel:
        subscription = await self._get_or_404(tenant_id, subscription_id)
        subscription.status = SubscriptionStatus.CANCELLED.value
        return await self.repos.event_subscriptions.update(subscription)

    async def list_for_topic(self, tenant_id: str, topic_id: str, *, active_only: bool = False) -> list[EventSubscriptionModel]:
        status = SubscriptionStatus.ACTIVE.value if active_only else None
        return await self.repos.event_subscriptions.list_for_topic(tenant_id, topic_id, status=status)

    async def _get_or_404(self, tenant_id: str, subscription_id: str) -> EventSubscriptionModel:
        subscription = await self.repos.event_subscriptions.get_or_404(subscription_id)
        if subscription.tenant_id != tenant_id:
            raise SubscriptionNotFoundError(f"subscription '{subscription_id}' not found for tenant '{tenant_id}'")
        return subscription
