from __future__ import annotations

import pytest

from gateway_platform.config.settings import Settings
from gateway_platform.core.exceptions import EventReplayWindowExceededError, TopicNotFoundError
from gateway_platform.events.event_bus_service import EventBusService
from gateway_platform.events.topic_service import EventTopicService

TENANT = "ev-bus-tenant"


@pytest.mark.asyncio
async def test_publish_and_deliver_success(repos):
    topics = EventTopicService(repos)
    topic = await topics.register_topic(TENANT, name="workflow.step", category="workflow")
    bus = EventBusService(repos)
    message = await bus.publish(TENANT, topic.id, payload={"step": 1})
    assert message.status == "published"

    delivered = await bus.attempt_delivery(TENANT, message.id)
    assert delivered.status == "delivered"
    assert delivered.delivered_at is not None


@pytest.mark.asyncio
async def test_publish_to_inactive_topic_rejected(repos):
    topics = EventTopicService(repos)
    topic = await topics.register_topic(TENANT, name="paused.topic", category="custom")
    await topics.pause_topic(TENANT, topic.id)
    bus = EventBusService(repos)
    with pytest.raises(TopicNotFoundError):
        await bus.publish(TENANT, topic.id, payload={})


@pytest.mark.asyncio
async def test_failed_delivery_retries_then_dead_letters(repos):
    settings = Settings(event_max_delivery_attempts=2)
    topics = EventTopicService(repos)
    topic = await topics.register_topic(TENANT, name="flaky.topic", category="custom")
    bus = EventBusService(repos, settings=settings)
    message = await bus.publish(TENANT, topic.id, payload={"x": 1})

    def always_fail(payload: dict) -> bool:
        return False

    failed_once = await bus.attempt_delivery(TENANT, message.id, deliverer=always_fail)
    assert failed_once.status == "failed"

    await bus.retry(TENANT, message.id)
    dead_lettered = await bus.attempt_delivery(TENANT, message.id, deliverer=always_fail)
    assert dead_lettered.status == "dead_lettered"

    dlq = await bus.list_dead_letters(TENANT, topic.id)
    assert len(dlq) == 1
    assert dlq[0].message_id == message.id


@pytest.mark.asyncio
async def test_replay_creates_new_message(repos):
    topics = EventTopicService(repos)
    topic = await topics.register_topic(TENANT, name="replay.topic", category="custom")
    bus = EventBusService(repos)
    original = await bus.publish(TENANT, topic.id, payload={"replayed": True})
    replayed = await bus.replay(TENANT, original.id)
    assert replayed.id != original.id
    assert replayed.payload == {"replayed": True}
    assert replayed.status == "published"


@pytest.mark.asyncio
async def test_replay_outside_window_rejected(repos):
    from datetime import timedelta

    settings = Settings(event_replay_window_days=7)
    topics = EventTopicService(repos)
    topic = await topics.register_topic(TENANT, name="stale.topic", category="custom")
    bus = EventBusService(repos, settings=settings)
    original = await bus.publish(TENANT, topic.id, payload={})
    original.published_at = original.published_at - timedelta(days=30)
    await repos.event_messages.update(original)

    with pytest.raises(EventReplayWindowExceededError):
        await bus.replay(TENANT, original.id)


@pytest.mark.asyncio
async def test_list_for_topic(repos):
    topics = EventTopicService(repos)
    topic = await topics.register_topic(TENANT, name="listable.topic", category="custom")
    bus = EventBusService(repos)
    await bus.publish(TENANT, topic.id, payload={"n": 1})
    await bus.publish(TENANT, topic.id, payload={"n": 2})
    messages = await bus.list_for_topic(TENANT, topic.id)
    assert len(messages) == 2
