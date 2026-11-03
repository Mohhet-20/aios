"""A couple of trivial, always-available connectors the engine itself
depends on for testing and for `category="custom"` tools with no
external system to call — `EchoHandler` (identity function, used for
"custom" tools that just want their input reflected/validated) and
`FunctionRegistryHandler` (dispatches to a plain in-process Python
callable registered by key, the same escape hatch the Workflow Engine's
`FunctionRegistryToolBridge` provides). Task 107 fills in the real
category-specific connectors (github, slack, http_client, ...) this
registry also carries."""
from __future__ import annotations

from typing import Any, Callable

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler


class EchoHandler(ConnectorHandler):
    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        return dict(ctx.input_data)


class FunctionRegistryHandler(ConnectorHandler):
    def __init__(self, functions: dict[str, Callable[..., Any]] | None = None):
        self._functions = dict(functions or {})

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        self._functions[name] = fn

    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        function_name = ctx.config.get("function_name") or ctx.input_data.get("function_name")
        if not function_name:
            raise ToolExecutionError("custom function tool call is missing 'function_name'")
        fn = self._functions.get(function_name)
        if fn is None:
            raise ToolExecutionError(f"no function registered under the name '{function_name}'")
        kwargs = {k: v for k, v in ctx.input_data.items() if k != "function_name"}
        result = fn(**kwargs)
        return result if isinstance(result, dict) else {"result": result}
