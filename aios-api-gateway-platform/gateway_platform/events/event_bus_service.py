"""Event bus: publish -> attempt delivery -> deliver/fail, with
failed messages retryable up to `event_max_delivery_attempts` before
being moved to the dead letter table. This mirrors the Webhook
Platform's delivery lifecycle exactly, because "publish an event, try
to deliver it, retry on failure, give up into a DLQ eventually" is the
same shape whether the transport is an HTTP callback or an in-process
event bus — the difference is only in what `deliver()` actually does,
which is why it's injected as a callable rather than hardcoded here."""
from __future__ import annotations

from collections.abc import Callable

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import EventNotFoundError, EventReplayWindowExceededError, TopicNotFoundError
from gateway_platform.database.base import utcnow
from gateway_platform.domain.entities import _aware
from gateway_platform.domain.enums import EventMessageStatus, TopicStatus
from gateway_platform.events.mappers import apply_event_message_domain_to_model, event_message_to_domain
from gateway_platform.models.events import DeadLetterEntryModel, EventMessageModel
from gateway_platform.repositories.registry import RepositoryRegistry

Deliverer = Callable[[dict], bool]


def _default_deliverer(payload: dict) -> bool:
    """No-op deliverer used when a caller doesn't supply one — treats
    every publish as instantly deliverable, matching an in-process bus
    with no real subscriber transport wired in yet."""
    return True


class EventBusService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def publish(self, tenant_id: str, topic_id: str, *, payload: dict) -> EventMessageModel:
        topic = await self.repos.event_topics.get_or_404(topic_id)
        if topic.tenant_id != tenant_id:
            raise TopicNotFoundError(f"topic '{topic_id}' not found for tenant '{tenant_id}'")
        if topic.status != TopicStatus.ACTIVE.value:
            raise TopicNotFoundError(f"topic '{topic_id}' is not active")
        message = EventMessageModel(
            tenant_id=tenant_id, topic_id=topic_id, payload=payload, status=EventMessageStatus.PUBLISHED.value,
        )
        return await self.repos.event_messages.add(message)

    async def attempt_delivery(
        self, tenant_id: str, message_id: str, *, deliverer: Deliverer = _default_deliverer,
    ) -> EventMessageModel:
        message = await self._get_or_404(tenant_id, message_id)
        message.attempt_count += 1
        entity = event_message_to_domain(message)

        if deliverer(message.payload):
            entity.deliver()
            apply_event_message_domain_to_model(entity, message)
            return await self.repos.event_messages.update(message)

        entity.fail()
        apply_event_message_domain_to_model(entity, message)
        message = await self.repos.event_messages.update(message)

        if message.attempt_count >= self.settings.event_max_delivery_attempts:
            entity = event_message_to_domain(message)
            entity.dead_letter()
            apply_event_message_domain_to_model(entity, message)
            message = await self.repos.event_messages.update(message)
            await self.repos.dead_letter_entries.add(
                DeadLetterEntryModel(
                    tenant_id=tenant_id, message_id=message.id, topic_id=message.topic_id,
                    reason=f"exceeded {self.settings.event_max_delivery_attempts} delivery attempts",
                )
            )
        return message

    async def retry(self, tenant_id: str, message_id: str) -> EventMessageModel:
        message = await self._get_or_404(tenant_id, message_id)
        entity = event_message_to_domain(message)
        entity.retry()
        apply_event_message_domain_to_model(entity, message)
        return await self.repos.event_messages.update(message)

    async def replay(self, tenant_id: str, message_id: str) -> EventMessageModel:
        original = await self._get_or_404(tenant_id, message_id)
        age_days = (utcnow() - _aware(original.published_at)).days
        if age_days > self.settings.event_replay_window_days:
            raise EventReplayWindowExceededError(
                f"message '{message_id}' is {age_days} days old, past the {self.settings.event_replay_window_days}-day replay window"
            )
        replayed = EventMessageModel(
            tenant_id=tenant_id, topic_id=original.topic_id, payload=original.payload,
            status=EventMessageStatus.PUBLISHED.value,
        )
        return await self.repos.event_messages.add(replayed)

    async def list_for_topic(self, tenant_id: str, topic_id: str, *, limit: int = 200) -> list[EventMessageModel]:
        return await self.repos.event_messages.list_for_topic(tenant_id, topic_id, limit=limit)

    async def list_dead_letters(self, tenant_id: str, topic_id: str) -> list[DeadLetterEntryModel]:
        return await self.repos.dead_letter_entries.list_for_topic(tenant_id, topic_id)

    async def _get_or_404(self, tenant_id: str, message_id: str) -> EventMessageModel:
        message = await self.repos.event_messages.get_or_404(message_id)
        if message.tenant_id != tenant_id:
            raise EventNotFoundError(f"event message '{message_id}' not found for tenant '{tenant_id}'")
        return message
