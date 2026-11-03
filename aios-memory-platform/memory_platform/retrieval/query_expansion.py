"""LLM-backed query expansion: turns one query into several rephrasings/
synonyms/related terms so retrieval isn't limited to the exact words the
caller typed — structured-output-validated via the AI Core's
`StructuredOutputEngine`, same pattern as document classification."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.structured_output.engine import StructuredOutputEngine


class QueryExpansion(BaseModel):
    expanded_queries: list[str] = Field(description="Alternate phrasings, synonyms, or related search queries — not including the original")


async def expand_query(ai_core: AICoreContext, query: str, *, max_expansions: int = 3) -> list[str]:
    messages = [
        ChatMessage(role=Role.SYSTEM, content=f"Generate up to {max_expansions} alternate phrasings or closely related search queries for the given search query. Keep them short."),
        ChatMessage(role=Role.USER, content=query),
    ]
    engine = StructuredOutputEngine(ai_core.execution_engine)
    result = await engine.execute(GenerationRequest(messages=messages, temperature=0.3), QueryExpansion)
    return result.instance.expanded_queries[:max_expansions]
