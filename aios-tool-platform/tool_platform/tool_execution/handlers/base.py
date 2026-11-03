"""ConnectorHandler: the uniform interface every tool category's
execution logic implements. `execute` returns the call's output dict.
`compensate` is only ever invoked for categories the caller explicitly
asked to roll back, during best-effort rollback after a downstream
failure — the default no-op is correct for the large majority of
read-only or non-side-effecting connectors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from tool_platform.tool_execution.context import ToolCallContext


class ConnectorHandler(ABC):
    @abstractmethod
    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]: ...

    async def compensate(self, ctx: ToolCallContext) -> None:
        """Default: nothing to roll back."""
        return None
