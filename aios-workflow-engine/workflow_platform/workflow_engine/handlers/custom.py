"""CUSTOM node handler: the escape hatch for a workspace-registered
callable that doesn't fit any of the other 29 built-in node types.
Dispatch is by `handler_key`, resolved through an injected registry — no
`exec()`/`eval()` of workspace-supplied code happens here; a custom
handler is a real Python callable a deploying organization registers
ahead of time, the same trust boundary a plugin system would use."""
from __future__ import annotations

from typing import Any

from workflow_platform.core.exceptions import NodeExecutionError
from workflow_platform.workflow_engine.context import NodeContext
from workflow_platform.workflow_engine.handlers.base import NodeHandler


class CustomHandler(NodeHandler):
    def __init__(self, *, registry: dict[str, Any] | None = None):
        self._registry = registry or {}

    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        handler_key = ctx.config.get("handler_key")
        fn = self._registry.get(handler_key)
        if fn is None:
            raise NodeExecutionError(f"no custom handler registered for handler_key '{handler_key}'")
        result = await fn(ctx)
        return result if isinstance(result, dict) else {"result": result}
