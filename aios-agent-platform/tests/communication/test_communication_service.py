import pytest

from agent_platform.communication.communication_service import CommunicationService
from agent_platform.communication.message_bus import EventBus
from agent_platform.domain.enums import MessageType


@pytest.mark.asyncio
async def test_send_direct_message(repos):
    svc = CommunicationService(repos)
    msg = await svc.send_direct("task1", "agent1", "agent2", "please review this")
    assert msg.message_type == MessageType.DIRECT.value
    assert msg.from_agent_id == "agent1"
    assert msg.to_agent_id == "agent2"


@pytest.mark.asyncio
async def test_broadcast_has_no_recipient(repos):
    svc = CommunicationService(repos)
    msg = await svc.broadcast("task1", "agent1", "starting work")
    assert msg.to_agent_id is None
    assert msg.message_type == MessageType.BROADCAST.value


@pytest.mark.asyncio
async def test_status_update_and_handoff(repos):
    svc = CommunicationService(repos)
    status = await svc.send_status_update("task1", "agent1", "50% complete")
    assert status.message_type == MessageType.STATUS_UPDATE.value

    handoff = await svc.send_handoff("task1", "agent1", "agent2", "over to you", structured_payload={"reason": "specialization"})
    assert handoff.message_type == MessageType.HANDOFF.value
    assert handoff.structured_payload == {"reason": "specialization"}


@pytest.mark.asyncio
async def test_log_event_and_stream_chunk(repos):
    svc = CommunicationService(repos)
    event = await svc.log_event("task1", "planner started")
    assert event.message_type == MessageType.EVENT.value
    assert event.from_agent_id is None

    chunk = await svc.send_stream_chunk("task1", "agent1", "partial output...", is_final=False)
    assert chunk.message_type == MessageType.STREAM_CHUNK.value
    assert chunk.structured_payload == {"is_final": False}


@pytest.mark.asyncio
async def test_get_conversation_returns_in_order(repos):
    svc = CommunicationService(repos)
    await svc.broadcast("task2", "agent1", "first")
    await svc.send_direct("task2", "agent1", "agent2", "second")
    await svc.log_event("task2", "third")

    conversation = await svc.get_conversation("task2")
    assert [m.content for m in conversation] == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_get_agent_messages_includes_sent_and_received(repos):
    svc = CommunicationService(repos)
    await svc.send_direct("task3", "agent1", "agent2", "to agent2")
    await svc.send_direct("task3", "agent3", "agent1", "to agent1")

    messages = await svc.get_agent_messages("agent1")
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_shared_workspace_set_get_update_list(repos):
    svc = CommunicationService(repos)
    await svc.set_shared_value("task4", "research_findings", {"summary": "v1"}, updated_by="agent1")
    value = await svc.get_shared_value("task4", "research_findings")
    assert value == {"summary": "v1"}

    await svc.set_shared_value("task4", "research_findings", {"summary": "v2"}, updated_by="agent2")
    updated = await svc.get_shared_value("task4", "research_findings")
    assert updated == {"summary": "v2"}

    await svc.set_shared_value("task4", "next_steps", {"steps": ["a", "b"]}, updated_by="agent1")
    entries = await svc.list_shared_workspace("task4")
    assert {e.key for e in entries} == {"research_findings", "next_steps"}


@pytest.mark.asyncio
async def test_shared_workspace_missing_key_returns_none(repos):
    svc = CommunicationService(repos)
    assert await svc.get_shared_value("task5", "nonexistent") is None


@pytest.mark.asyncio
async def test_event_bus_receives_published_messages(repos):
    bus = EventBus()
    received = []

    async def handler(payload):
        received.append(payload)

    bus.subscribe("message.sent", handler)
    svc = CommunicationService(repos, event_bus=bus)
    await svc.send_direct("task6", "agent1", "agent2", "hello")

    assert len(received) == 1
    assert received[0]["content"] == "hello"


@pytest.mark.asyncio
async def test_event_bus_wildcard_subscriber_and_unsubscribe():
    bus = EventBus()
    calls = []

    def handler(payload):
        calls.append(payload)

    bus.subscribe("*", handler)
    await bus.publish("anything", {"x": 1})
    assert len(calls) == 1

    bus.unsubscribe("*", handler)
    await bus.publish("anything", {"x": 2})
    assert len(calls) == 1  # unsubscribed, no new call
