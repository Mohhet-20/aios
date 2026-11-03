"""LLM-backed content classification — structured-output-validated (via
the AI Core's `StructuredOutputEngine`, the same pattern the Agent
Platform's reasoning engine uses) so a document gets a typed
categories/topics/confidence result, not free text hoped to be parseable.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.structured_output.engine import StructuredOutputEngine


class DocumentClassification(BaseModel):
    categories: list[str] = Field(description="High-level topical categories, e.g. ['finance', 'legal']")
    topics: list[str] = Field(default_factory=list, description="Finer-grained topics/keywords mentioned in the document")
    language: str = Field(default="en", description="Best-guess ISO 639-1 language code")
    confidence: float = Field(ge=0.0, le=1.0)


async def classify_document(ai_core: AICoreContext, text: str, *, max_chars: int = 6000) -> DocumentClassification:
    excerpt = text[:max_chars]
    messages = [
        ChatMessage(role=Role.SYSTEM, content="Classify this document. Return concise, high-level categories and specific topics."),
        ChatMessage(role=Role.USER, content=excerpt),
    ]
    engine = StructuredOutputEngine(ai_core.execution_engine)
    result = await engine.execute(GenerationRequest(messages=messages, temperature=0.1), DocumentClassification)
    return result.instance
