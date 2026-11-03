"""ConversationMemoryService — turns of a single conversation, ordered
by `turn_index`, with LLM-backed running-summary compression once the
transcript crosses the CONVERSATION type's `summarize_after_tokens`
policy. Built on top of `MemoryService` rather than duplicating its
lifecycle logic."""
from __future__ import annotations

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.tokenizer.counter import count_tokens

from memory_platform.domain.enums import MemoryType
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.models.memory_entry import MemoryEntryModel
from memory_platform.repositories.registry import RepositoryRegistry


class ConversationMemoryService:
    def __init__(self, repos: RepositoryRegistry, memory_service: MemoryService, *, ai_core: AICoreContext | None = None):
        self.repos = repos
        self.memory_service = memory_service
        self.ai_core = ai_core

    async def append_turn(
        self, *, workspace_id: str, conversation_id: str, scope_type: str, scope_id: str, role: str, content: str, actor_id: str = "system",
    ) -> MemoryEntryModel:
        existing = await self.repos.memory_entries.list_by_conversation(conversation_id)
        next_index = (max((t.turn_index or 0) for t in existing) + 1) if existing else 0
        return await self.memory_service.create(
            workspace_id=workspace_id, memory_type=MemoryType.CONVERSATION, scope_type=scope_type, scope_id=scope_id,
            content=content, actor_id=actor_id, structured_content={"role": role}, conversation_id=conversation_id, turn_index=next_index,
        )

    async def get_transcript(self, conversation_id: str) -> list[MemoryEntryModel]:
        return await self.repos.memory_entries.list_by_conversation(conversation_id)

    async def total_tokens(self, conversation_id: str) -> int:
        turns = await self.get_transcript(conversation_id)
        return sum(count_tokens(t.content) for t in turns)

    async def summarize_if_long(self, conversation_id: str, *, actor_id: str = "system") -> str | None:
        """Real compression: once the transcript's token count crosses the
        CONVERSATION policy's `summarize_after_tokens`, produce a running
        summary via the LLM and return it (callers may store it as a
        LONG_TERM memory or attach it to the conversation however they see fit)."""
        if self.ai_core is None:
            return None
        policy = await self.repos.memory_type_policies.get_by_key(MemoryType.CONVERSATION.value)
        threshold = policy.summarize_after_tokens if policy else None
        if threshold is None:
            return None
        turns = await self.get_transcript(conversation_id)
        total = sum(count_tokens(t.content) for t in turns)
        if total < threshold:
            return None
        transcript_text = "\n".join(f"[{(t.structured_content or {}).get('role', 'unknown')}] {t.content}" for t in turns)
        messages = [
            ChatMessage(role=Role.SYSTEM, content="Summarize this conversation, preserving key facts, decisions, and open questions, in under 250 tokens."),
            ChatMessage(role=Role.USER, content=transcript_text),
        ]
        response = await self.ai_core.execution_engine.generate(GenerationRequest(messages=messages, temperature=0.2))
        return response.content.strip()
