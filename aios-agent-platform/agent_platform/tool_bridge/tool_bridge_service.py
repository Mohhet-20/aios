"""Tool Integration: the real bridge between an agent's platform-level
tool permissions (AgentToolPermissionModel — "can this agent even attempt
this tool") and the AI Core's own tool-calling machinery (ToolRegistry /
ToolExecutor — "does this tool exist and how do I run it"). Two
independent gates on purpose: the AI Core's ToolDefinition.requires_permission
is a generic capability tag any caller can define; AgentToolPermissionModel
is this platform's own per-agent RBAC on top of it. A tool call has to
clear both.
"""
from __future__ import annotations

import structlog

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.tools import ToolCall, ToolDefinition, ToolResult
from ai_core.tool_calling.mcp_compat import from_mcp_tool_spec

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.domain.enums import ToolPermissionLevel
from agent_platform.repositories.registry import RepositoryRegistry

logger = structlog.get_logger(__name__)


class ToolBridgeService:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext):
        self.repos = repos
        self.ai_core = ai_core
        self.agent_service = AgentService(repos)

    async def available_tools(self, agent_id: str, *, minimum: ToolPermissionLevel = ToolPermissionLevel.EXECUTE) -> list[ToolDefinition]:
        """Only the tools both registered in the AI Core AND granted to
        this agent at or above `minimum` — what actually gets attached to
        the agent's next GenerationRequest."""
        grants = await self.repos.tool_permissions.list_for_agent(agent_id)
        order = [ToolPermissionLevel.NONE, ToolPermissionLevel.READ_ONLY, ToolPermissionLevel.EXECUTE, ToolPermissionLevel.FULL]
        permitted = {g.tool_name for g in grants if order.index(ToolPermissionLevel(g.permission_level)) >= order.index(minimum)}
        return [d for d in self.ai_core.tool_registry.definitions() if d.name in permitted]

    async def invoke(self, agent_id: str, tool_call: ToolCall, *, minimum: ToolPermissionLevel = ToolPermissionLevel.EXECUTE) -> ToolResult:
        allowed = await self.agent_service.has_tool_permission(agent_id, tool_call.name, minimum=minimum)
        if not allowed:
            logger.warning("tool_call_denied", agent_id=agent_id, tool_name=tool_call.name, minimum=minimum.value)
            return ToolResult(
                tool_call_id=tool_call.id, name=tool_call.name, is_error=True,
                error=f"agent '{agent_id}' does not have '{minimum.value}' permission for tool '{tool_call.name}'",
            )
        return await self.ai_core.tool_executor.execute_one(tool_call)

    async def invoke_many(self, agent_id: str, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Sequential on purpose: tool calls made on behalf of an agent may
        touch the same DB session as everything else in that agent's turn
        (permission lookups), and AsyncSession is not safe for concurrent
        use — see TaskOrchestrator's own session_lock for the same lesson
        learned at the orchestration layer."""
        return [await self.invoke(agent_id, tc) for tc in tool_calls]

    # -- MCP forward-compatibility passthrough -----------------------------------

    def register_mcp_tool(self, mcp_spec: dict, handler) -> ToolDefinition:
        """Registers an MCP-shaped tool spec (`{name, description,
        inputSchema}`) directly into the AI Core's ToolRegistry via the
        existing `from_mcp_tool_spec` bridge — the tool-calling contract an
        agent sees (ToolCall/ToolResult) never changes regardless of
        whether the tool is first-party or MCP-sourced."""
        definition = from_mcp_tool_spec(mcp_spec)
        self.ai_core.tool_registry.register(definition, handler)
        return definition
