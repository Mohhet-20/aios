from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import ValidationError
from gateway_platform.events.topic_service import EventTopicService

TENANT = "ev-tenant"


@pytest.mark.asyncio
async def test_register_topic_idempotent_by_name(repos):
    service = EventTopicService(repos)
    a = await service.register_topic(TENANT, name="workflow.completed", category="workflow")
    b = await service.register_topic(TENANT, name="workflow.completed", category="workflow")
    assert a.id == b.id


@pytest.mark.asyncio
async def test_invalid_category_rejected(repos):
    service = EventTopicService(repos)
    with pytest.raises(ValidationError):
        await service.register_topic(TENANT, name="bad.topic", category="not-a-category")


@pytest.mark.asyncio
async def test_pause_resume_retire_lifecycle(repos):
    service = EventTopicService(repos)
    topic = await service.register_topic(TENANT, name="agent.spawned", category="agent")
    paused = await service.pause_topic(TENANT, topic.id)
    assert paused.status == "paused"
    resumed = await service.resume_topic(TENANT, topic.id)
    assert resumed.status == "active"
    retired = await service.retire_topic(TENANT, topic.id)
    assert retired.status == "retired"


@pytest.mark.asyncio
async def test_list_for_tenant(repos):
    service = EventTopicService(repos)
    await service.register_topic(TENANT, name="system.alert", category="system")
    topics = await service.list_for_tenant(TENANT)
    assert any(t.name == "system.alert" for t in topics)
