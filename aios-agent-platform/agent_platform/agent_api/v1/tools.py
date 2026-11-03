"""Tool Integration: which tools an agent may see (permission-filtered
against the AI Core's own ToolRegistry) and invoking one directly for
inspection/testing. Registering new tool handlers is a backend
integration concern (a live Python callable can't cross an HTTP
boundary), so it's intentionally not exposed here — see
`ToolBridgeService.register_mcp_tool` for that seam."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ai_core.schemas.tools import ToolCall

from agent_platform.agent_api.dependencies import get_tool_bridge_service
from agent_platform.tool_bridge.tool_bridge_service import ToolBridgeService

router = APIRouter(prefix="/agents/{agent_id}/tools", tags=["tools"])


class InvokeToolRequest(BaseModel):
    tool_call_id: str
    name: str
    arguments: dict = {}


@router.get("")
async def available_tools(agent_id: str, bridge: ToolBridgeService = Depends(get_tool_bridge_service)):
    tools = await bridge.available_tools(agent_id)
    return [t.model_dump() for t in tools]


@router.post("/invoke")
async def invoke_tool(agent_id: str, body: InvokeToolRequest, bridge: ToolBridgeService = Depends(get_tool_bridge_service)):
    result = await bridge.invoke(agent_id, ToolCall(id=body.tool_call_id, name=body.name, arguments=body.arguments))
    return result.model_dump()
