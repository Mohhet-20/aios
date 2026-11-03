"""ConversationService — backs the Inference Studio conversation timeline.
Kept distinct from InferenceService: a conversation is a persisted thread of
messages (what the user sees and revisits), while InferenceService is a
stateless single-call gateway to a model. A future "agent chat" endpoint
composes both: append to a conversation, then call InferenceService with
that conversation's history as context.
"""

from __future__ import annotations

from app.clock import utc_now
from app.models.conversation import ConversationMessageModel, ConversationModel
from app.repositories.conversation_repository import ConversationMessageRepository, ConversationRepository


class ConversationService:
    def __init__(self, conversations: ConversationRepository, messages: ConversationMessageRepository):
        self.conversations = conversations
        self.messages = messages

    async def start(
        self, workspace_id: str, user_id: str, agent_id: str | None, title: str = ""
    ) -> ConversationModel:
        conversation = ConversationModel(
            workspace_id=workspace_id, user_id=user_id, agent_id=agent_id, title=title
        )
        return await self.conversations.add(conversation)

    async def add_message(
        self, conversation_id: str, role: str, content: str, tool_calls: list | None = None
    ) -> ConversationMessageModel:
        message = ConversationMessageModel(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            created_at=utc_now(),
        )
        return await self.messages.add(message)

    async def get_history(self, conversation_id: str) -> list[ConversationMessageModel]:
        return await self.messages.list_for_conversation(conversation_id)
