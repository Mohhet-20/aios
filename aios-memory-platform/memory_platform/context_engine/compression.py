"""LLM-backed context compression — used when the assembled context
still exceeds its token budget after duplicate removal and per-item
truncation. Same structured pattern as document/memory summarization
elsewhere in this platform: a real model call, not a heuristic
truncation dressed up as "summarization" (that's what
`RetrievalService.compress_content` / per-item truncation are for)."""
from __future__ import annotations

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest


async def summarize_context(ai_core: AICoreContext, text: str, *, max_summary_tokens: int = 500) -> str:
    messages = [
        ChatMessage(role=Role.SYSTEM, content=f"Condense the following retrieved context into at most {max_summary_tokens} tokens, preserving every distinct fact and its source label. Do not invent information."),
        ChatMessage(role=Role.USER, content=text),
    ]
    response = await ai_core.execution_engine.generate(GenerationRequest(messages=messages, temperature=0.1))
    return response.content.strip()
