"""Tool/function-calling schemas shared by the tool registry, the execution
engine, and every provider adapter's tool-call translation logic."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ai_core.schemas.enums import ToolSideEffect


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []},
        description="JSON Schema for the tool's arguments, in the same shape OpenAI/Anthropic function-calling expects.",
    )
    side_effect: ToolSideEffect = ToolSideEffect.NONE
    requires_permission: str | None = Field(
        default=None, description="Dotted permission string the caller's Principal must hold, e.g. 'tool:web_search'."
    )
    timeout_seconds: float = 15.0


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_call_id: str
    name: str
    content: Any = None
    is_error: bool = False
    error: str | None = None
