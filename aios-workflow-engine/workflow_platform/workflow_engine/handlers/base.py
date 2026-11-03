"""NodeHandler: the uniform interface every node type's execution logic
implements. `execute` returns the node's output dict (merged into
execution context by the engine). `compensate` is only ever invoked for
node types marked `is_compensable=True` on their `NodeDefinitionModel`,
during saga-style rollback after a downstream failure — the default
no-op is correct for the large majority of (non-side-effecting) node
types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from workflow_platform.workflow_engine.context import NodeContext


class NodeHandler(ABC):
    @abstractmethod
    async def execute(self, ctx: NodeContext) -> dict[str, Any]: ...

    async def compensate(self, ctx: NodeContext) -> None:
        """Default: nothing to roll back."""
        return None
