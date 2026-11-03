"""AI-category node handlers. LLM_CALL and EMBEDDING_GENERATOR call AI
Core directly (real integration — the same `AICoreContext` every other
AIOS platform wires in). AGENT, PROMPT, MEMORY_READ, MEMORY_WRITE,
RETRIEVER, KNOWLEDGE_SEARCH, and DOCUMENT_PARSER go through the bridge
Protocols in `ai_bridges/interfaces.py` — see that module's docstring for
why the engine never imports a sibling platform directly."""
from __future__ import annotations

from typing import Any

from workflow_platform.core.exceptions import NodeExecutionError
from workflow_platform.workflow_engine.context import NodeContext
from workflow_platform.workflow_engine.handlers.base import NodeHandler


class LlmCallHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.ai_core is None:
            raise NodeExecutionError("LLM_CALL node requires an AICoreContext to be configured on the engine")
        from ai_core.schemas.enums import Role
        from ai_core.schemas.messages import ChatMessage
        from ai_core.schemas.requests import GenerationRequest

        prompt_text = ctx.config.get("prompt") or ctx.variables.get("prompt", "")
        rendered = prompt_text.format(**ctx.variables) if isinstance(prompt_text, str) else str(prompt_text)
        request = GenerationRequest(
            messages=[ChatMessage(role=Role.USER, content=rendered)],
            model=ctx.config.get("model"), provider=ctx.config.get("provider"),
            temperature=ctx.config.get("temperature", 0.7), max_tokens=ctx.config.get("max_tokens"),
        )
        response = await ctx.ai_core.execution_engine.generate(request)
        return {
            "content": response.content, "finish_reason": response.finish_reason.value if hasattr(response.finish_reason, "value") else response.finish_reason,
            "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens,
            "provider": response.execution.provider, "model": response.execution.model,
        }


class EmbeddingGeneratorHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.ai_core is None:
            raise NodeExecutionError("EMBEDDING_GENERATOR node requires an AICoreContext to be configured on the engine")
        from ai_core.schemas.requests import EmbeddingRequest

        text_input = ctx.config.get("input") or ctx.variables.get("text", "")
        request = EmbeddingRequest(input=text_input, model=ctx.config.get("model"), provider=ctx.config.get("provider"))
        response = await ctx.ai_core.embedding_engine.embed(request)
        return {"embeddings": response.embeddings, "dimensions": response.dimensions, "model": response.model}


class AgentHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.bridges.agent is None:
            raise NodeExecutionError("AGENT node requires an AgentBridge to be configured on the engine")
        agent_id = ctx.config.get("agent_id")
        task = ctx.config.get("task", "").format(**ctx.variables) if isinstance(ctx.config.get("task"), str) else ctx.config.get("task")
        return await ctx.bridges.agent.run_agent(agent_id, task=task, context=dict(ctx.variables))


class PromptHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.bridges.prompt is None:
            raise NodeExecutionError("PROMPT node requires a PromptBridge to be configured on the engine")
        prompt_id = ctx.config.get("prompt_id")
        variables = {**ctx.variables, **(ctx.config.get("variables") or {})}
        return await ctx.bridges.prompt.run_prompt(prompt_id, variables=variables)


class MemoryReadHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.bridges.memory is None:
            raise NodeExecutionError("MEMORY_READ node requires a MemoryBridge to be configured on the engine")
        return await ctx.bridges.memory.read_memory(scope=ctx.config.get("scope", "workflow"), query=ctx.config.get("query", {}))


class MemoryWriteHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.bridges.memory is None:
            raise NodeExecutionError("MEMORY_WRITE node requires a MemoryBridge to be configured on the engine")
        content = ctx.config.get("content") or {"variables": dict(ctx.variables)}
        return await ctx.bridges.memory.write_memory(scope=ctx.config.get("scope", "workflow"), content=content)

    async def compensate(self, ctx: NodeContext) -> None:
        if ctx.bridges.memory is None:
            return
        write_ref = ctx.node_execution.output_data.get("write_ref")
        if write_ref:
            await ctx.bridges.memory.undo_write(scope=ctx.config.get("scope", "workflow"), write_ref=write_ref)


class RetrieverHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.bridges.memory is None:
            raise NodeExecutionError("RETRIEVER node requires a MemoryBridge to be configured on the engine")
        query = ctx.config.get("query", "").format(**ctx.variables) if isinstance(ctx.config.get("query"), str) else ctx.config.get("query", "")
        return await ctx.bridges.memory.retrieve(query=query, top_k=ctx.config.get("top_k", 5))


class KnowledgeSearchHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.bridges.knowledge is None:
            raise NodeExecutionError("KNOWLEDGE_SEARCH node requires a KnowledgeBridge to be configured on the engine")
        return await ctx.bridges.knowledge.search(query=ctx.config.get("query", ""), top_k=ctx.config.get("top_k", 5))


class DocumentParserHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.bridges.document_intelligence is None:
            raise NodeExecutionError("DOCUMENT_PARSER node requires a DocumentIntelligenceBridge to be configured on the engine")
        file_ref = ctx.config.get("file_ref") or ctx.variables.get("file_ref")
        return await ctx.bridges.document_intelligence.parse_document(file_ref=file_ref, mime_type=ctx.config.get("mime_type"))


class FunctionCallHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        if ctx.bridges.tool is None:
            raise NodeExecutionError("FUNCTION_CALL node requires a ToolBridge to be configured on the engine")
        function_name = ctx.config.get("function_name")
        arguments = {**(ctx.config.get("arguments") or {})}
        return await ctx.bridges.tool.call_function(function_name, arguments=arguments)
