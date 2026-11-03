"""EmbeddingGeneratorHandler: a real call into the AI Core's embedding
engine — the same `ai_core` injection seam the Workflow Engine's
EMBEDDING_GENERATOR node handler uses, so this connector never has its
own provider logic to duplicate or drift from the AI Core's."""
from __future__ import annotations

from typing import Any

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler


class EmbeddingGeneratorHandler(ConnectorHandler):
    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        if ctx.ai_core is None:
            raise ToolExecutionError("embedding_generator tool call requires an AICoreContext to be configured on the engine")
        from ai_core.schemas.requests import EmbeddingRequest

        text_input = ctx.input_data.get("input") or ctx.config.get("input", "")
        request = EmbeddingRequest(input=text_input, model=ctx.config.get("model"), provider=ctx.config.get("provider"))
        response = await ctx.ai_core.embedding_engine.embed(request)
        return {"embeddings": response.embeddings, "dimensions": response.dimensions, "model": response.model}
