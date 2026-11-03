"""Inter-Agent Communication: direct messages, broadcasts, status
updates, handoffs, event/log entries, and streaming chunks — all
persisted as MessageModel rows for later inspection (the Conversation
Inspector frontend surface reads straight from `get_conversation`) and
mirrored onto the EventBus for real-time subscribers. Also owns the
per-task shared workspace (blackboard) agents read/write for
collaboration that doesn't fit a point-to-point message.
"""
from __future__ import annotations

from agent_platform.communication.message_bus import EventBus
from agent_platform.domain.enums import MessageType
from agent_platform.models.message import MessageModel, SharedWorkspaceEntryModel
from agent_platform.repositories.registry import RepositoryRegistry


class CommunicationService:
    def __init__(self, repos: RepositoryRegistry, *, event_bus: EventBus | None = None):
        self.repos = repos
        self.event_bus = event_bus or EventBus()

    async def _send(
        self, *, task_id: str | None, from_agent_id: str | None, to_agent_id: str | None,
        message_type: MessageType, content: str, structured_payload: dict | None = None,
    ) -> MessageModel:
        message = await self.repos.messages.add(MessageModel(
            task_id=task_id, from_agent_id=from_agent_id, to_agent_id=to_agent_id,
            message_type=message_type.value, content=content, structured_payload=structured_payload,
        ))
        await self.event_bus.publish("message.sent", {
            "id": message.id, "task_id": task_id, "from_agent_id": from_agent_id, "to_agent_id": to_agent_id,
            "message_type": message_type.value, "content": content,
        })
        return message

    async def send_direct(self, task_id: str | None, from_agent_id: str, to_agent_id: str, content: str, *, structured_payload: dict | None = None) -> MessageModel:
        return await self._send(task_id=task_id, from_agent_id=from_agent_id, to_agent_id=to_agent_id, message_type=MessageType.DIRECT, content=content, structured_payload=structured_payload)

    async def broadcast(self, task_id: str | None, from_agent_id: str | None, content: str, *, structured_payload: dict | None = None) -> MessageModel:
        return await self._send(task_id=task_id, from_agent_id=from_agent_id, to_agent_id=None, message_type=MessageType.BROADCAST, content=content, structured_payload=structured_payload)

    async def send_status_update(self, task_id: str, agent_id: str, status_text: str, *, structured_payload: dict | None = None) -> MessageModel:
        return await self._send(task_id=task_id, from_agent_id=agent_id, to_agent_id=None, message_type=MessageType.STATUS_UPDATE, content=status_text, structured_payload=structured_payload)

    async def send_handoff(self, task_id: str, from_agent_id: str | None, to_agent_id: str, content: str, *, structured_payload: dict | None = None) -> MessageModel:
        return await self._send(task_id=task_id, from_agent_id=from_agent_id, to_agent_id=to_agent_id, message_type=MessageType.HANDOFF, content=content, structured_payload=structured_payload)

    async def log_event(self, task_id: str | None, content: str, *, structured_payload: dict | None = None) -> MessageModel:
        return await self._send(task_id=task_id, from_agent_id=None, to_agent_id=None, message_type=MessageType.EVENT, content=content, structured_payload=structured_payload)

    async def send_stream_chunk(self, task_id: str, agent_id: str, chunk_text: str, *, is_final: bool = False) -> MessageModel:
        return await self._send(
            task_id=task_id, from_agent_id=agent_id, to_agent_id=None, message_type=MessageType.STREAM_CHUNK,
            content=chunk_text, structured_payload={"is_final": is_final},
        )

    async def log(self, task_id: str | None, content: str) -> MessageModel:
        return await self._send(task_id=task_id, from_agent_id=None, to_agent_id=None, message_type=MessageType.LOG, content=content)

    # -- retrieval -------------------------------------------------------------

    async def get_conversation(self, task_id: str) -> list[MessageModel]:
        return await self.repos.messages.list_for_task(task_id)

    async def get_agent_messages(self, agent_id: str) -> list[MessageModel]:
        return await self.repos.messages.list_for_agent(agent_id)

    # -- shared workspace (blackboard) --------------------------------------------

    async def set_shared_value(self, task_id: str, key: str, value: dict, *, updated_by: str | None = None) -> SharedWorkspaceEntryModel:
        existing = await self.repos.shared_workspace.get_by_key(task_id, key)
        if existing is not None:
            existing.value = value
            existing.updated_by = updated_by
            return await self.repos.shared_workspace.update(existing)
        return await self.repos.shared_workspace.add(SharedWorkspaceEntryModel(task_id=task_id, key=key, value=value, updated_by=updated_by))

    async def get_shared_value(self, task_id: str, key: str) -> dict | None:
        entry = await self.repos.shared_workspace.get_by_key(task_id, key)
        return entry.value if entry else None

    async def list_shared_workspace(self, task_id: str) -> list[SharedWorkspaceEntryModel]:
        return await self.repos.shared_workspace.list_for_task(task_id)
