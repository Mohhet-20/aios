"""Event topics: one per stream, categorized by the taxonomy the
prompt specifies (workflow/agent/prompt/security/system/custom).
`register_topic` is a get-or-create by name — re-declaring a topic a
publisher already announced returns the existing row rather than
erroring."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from gateway_platform.core.exceptions import TopicNotFoundError, ValidationError
from gateway_platform.domain.enums import EventCategory, TopicStatus
from gateway_platform.models.events import EventTopicModel
from gateway_platform.repositories.registry import RepositoryRegistry


class EventTopicService:
    """`register_topic` is a get-or-create keyed on `(tenant_id,
    name)` — guarded with an in-process `asyncio.Lock` per key, the
    same commit-spanning-lock pattern used across every other AIOS
    services's own "upsert by identity" methods, since two concurrent
    publishers announcing the same topic name for the first time would
    otherwise both observe no existing row and both insert, producing
    a duplicate topic."""

    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_category(self, category: str) -> None:
        if category not in {c.value for c in EventCategory}:
            raise ValidationError(f"'{category}' is not a recognized event category")

    async def register_topic(self, tenant_id: str, *, name: str, category: str = "custom") -> EventTopicModel:
        self._assert_valid_category(category)
        lock_key = f"{tenant_id}:{name}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.event_topics.get_by_name(tenant_id, name)
            if existing is not None:
                return existing
            topic = EventTopicModel(tenant_id=tenant_id, name=name, category=category, status=TopicStatus.ACTIVE.value)
            topic = await self.repos.event_topics.add(topic)
            # Commit while still holding the lock — see ConnectorService's
            # identical note on why this must happen before release.
            await self.repos.session.commit()
            return topic

    async def pause_topic(self, tenant_id: str, topic_id: str) -> EventTopicModel:
        topic = await self._get_or_404(tenant_id, topic_id)
        topic.status = TopicStatus.PAUSED.value
        return await self.repos.event_topics.update(topic)

    async def resume_topic(self, tenant_id: str, topic_id: str) -> EventTopicModel:
        topic = await self._get_or_404(tenant_id, topic_id)
        topic.status = TopicStatus.ACTIVE.value
        return await self.repos.event_topics.update(topic)

    async def retire_topic(self, tenant_id: str, topic_id: str) -> EventTopicModel:
        topic = await self._get_or_404(tenant_id, topic_id)
        topic.status = TopicStatus.RETIRED.value
        return await self.repos.event_topics.update(topic)

    async def list_for_tenant(self, tenant_id: str) -> list[EventTopicModel]:
        return await self.repos.event_topics.list_for_tenant(tenant_id)

    async def _get_or_404(self, tenant_id: str, topic_id: str) -> EventTopicModel:
        topic = await self.repos.event_topics.get_or_404(topic_id)
        if topic.tenant_id != tenant_id:
            raise TopicNotFoundError(f"topic '{topic_id}' not found for tenant '{tenant_id}'")
        return topic
