from __future__ import annotations

import pytest

from gateway_platform.events.subscription_service import EventSubscriptionService, matches_filter
from gateway_platform.events.topic_service import EventTopicService

TENANT = "ev-sub-tenant"


def test_matches_filter_empty_matches_everything():
    assert matches_filter({"a": 1}, {}) is True


def test_matches_filter_checks_equality():
    assert matches_filter({"status": "ok", "code": 200}, {"status": "ok"}) is True
    assert matches_filter({"status": "fail"}, {"status": "ok"}) is False


@pytest.mark.asyncio
async def test_subscribe_and_list_for_topic(repos):
    topics = EventTopicService(repos)
    topic = await topics.register_topic(TENANT, name="prompt.executed", category="prompt")
    subs = EventSubscriptionService(repos)
    await subs.subscribe(TENANT, topic.id, subscriber="analytics-worker")
    listed = await subs.list_for_topic(TENANT, topic.id)
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_pause_resume_cancel_lifecycle(repos):
    topics = EventTopicService(repos)
    topic = await topics.register_topic(TENANT, name="security.alert", category="security")
    subs = EventSubscriptionService(repos)
    subscription = await subs.subscribe(TENANT, topic.id, subscriber="siem-worker")

    paused = await subs.pause(TENANT, subscription.id)
    assert paused.status == "paused"
    active_only = await subs.list_for_topic(TENANT, topic.id, active_only=True)
    assert active_only == []

    resumed = await subs.resume(TENANT, subscription.id)
    assert resumed.status == "active"
    cancelled = await subs.cancel(TENANT, subscription.id)
    assert cancelled.status == "cancelled"
