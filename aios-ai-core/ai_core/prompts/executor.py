"""Ties prompt rendering to the execution engine: render templates ->
build a GenerationRequest -> run it through ExecutionEngine -> optionally
postprocess the output text. This is "structured prompt execution" in the
non-schema sense (structured *inputs*); see structured_output/ for
schema-validated *outputs*, which PromptExecutor also exposes a passthrough
for via `response_format`.
"""
from __future__ import annotations

from collections.abc import Callable

from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.prompts.composer import render_messages
from ai_core.prompts.template import PromptTemplate
from ai_core.schemas.requests import GenerationRequest, RoutingHints, UsageContext
from ai_core.schemas.responses import GenerationResponse
from ai_core.schemas.tools import ToolDefinition


class PromptExecutor:
    def __init__(self, engine: ExecutionEngine):
        self.engine = engine

    async def execute(
        self,
        templates: list[PromptTemplate],
        variables: dict | None = None,
        *,
        model: str | None = None,
        provider: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[ToolDefinition] | None = None,
        response_format: dict | None = None,
        usage_context: UsageContext | None = None,
        routing_hints: RoutingHints | None = None,
        postprocess: Callable[[str], str] | None = None,
    ) -> GenerationResponse:
        messages = render_messages(templates, variables)
        request = GenerationRequest(
            messages=messages,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            response_format=response_format,
            usage_context=usage_context or UsageContext(),
            routing_hints=routing_hints or RoutingHints(),
        )
        response = await self.engine.generate(request)
        if postprocess is not None:
            response.content = postprocess(response.content)
        return response
