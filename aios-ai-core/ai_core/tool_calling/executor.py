"""Executes model-requested tool calls: permission check, argument
validation, sandboxed invocation with a per-tool timeout, and a
ToolResult back — in both parallel (default; tools are usually
independent) and sequential (when call order matters, e.g. one tool's
result should be visible before the next runs) modes. Every path returns
a ToolResult, even on failure — a failed tool call is reported back to the
model as an error result, not raised to the caller, since "the model asked
for something invalid" is an expected, recoverable case.
"""
from __future__ import annotations

import asyncio

from ai_core.schemas.tools import ToolCall, ToolResult
from ai_core.tool_calling.registry import ToolRegistry
from ai_core.tool_calling.sandbox import NullToolSandbox, ToolSandbox
from ai_core.tool_calling.validation import validate_tool_arguments
from ai_core.utils.exceptions import ToolExecutionError, ToolNotFoundError


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, *, sandbox: ToolSandbox | None = None):
        self.registry = registry
        self.sandbox = sandbox or NullToolSandbox()

    async def execute_one(self, tool_call: ToolCall, *, granted_permissions: set[str] | None = None) -> ToolResult:
        granted = granted_permissions or set()
        try:
            entry = self.registry.get(tool_call.name)
        except ToolNotFoundError as exc:
            return ToolResult(tool_call_id=tool_call.id, name=tool_call.name, is_error=True, error=str(exc))

        definition, handler = entry.definition, entry.handler

        if definition.requires_permission and definition.requires_permission not in granted:
            return ToolResult(
                tool_call_id=tool_call.id, name=tool_call.name, is_error=True,
                error=f"permission denied: '{definition.requires_permission}' required to call '{tool_call.name}'",
            )

        try:
            validate_tool_arguments(definition, tool_call.arguments)
        except ToolExecutionError as exc:
            return ToolResult(tool_call_id=tool_call.id, name=tool_call.name, is_error=True, error=str(exc))

        try:
            result = await asyncio.wait_for(
                self.sandbox.run(handler, tool_call.arguments), timeout=definition.timeout_seconds
            )
        except asyncio.TimeoutError:
            return ToolResult(
                tool_call_id=tool_call.id, name=tool_call.name, is_error=True,
                error=f"tool '{tool_call.name}' timed out after {definition.timeout_seconds}s",
            )
        except Exception as exc:  # noqa: BLE001 — any handler failure becomes an error result, not a crash
            return ToolResult(tool_call_id=tool_call.id, name=tool_call.name, is_error=True, error=str(exc))

        return ToolResult(tool_call_id=tool_call.id, name=tool_call.name, content=result, is_error=False)

    async def execute_parallel(
        self, tool_calls: list[ToolCall], *, granted_permissions: set[str] | None = None
    ) -> list[ToolResult]:
        return list(
            await asyncio.gather(*[self.execute_one(tc, granted_permissions=granted_permissions) for tc in tool_calls])
        )

    async def execute_sequential(
        self, tool_calls: list[ToolCall], *, granted_permissions: set[str] | None = None
    ) -> list[ToolResult]:
        results = []
        for tc in tool_calls:
            results.append(await self.execute_one(tc, granted_permissions=granted_permissions))
        return results
