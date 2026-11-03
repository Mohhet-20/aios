"""NodeContext: everything a node handler needs to do its job, bundled
so handler signatures stay uniform (`execute(ctx)` / `compensate(ctx)`)
regardless of what the node actually does. `variables` is a live
reference to the execution's in-flight context — handlers mutate it
directly (that's how a node's output becomes visible to later nodes)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from workflow_platform.ai_bridges.interfaces import BridgeSet
from workflow_platform.models.execution import ExecutionModel, NodeExecutionModel
from workflow_platform.models.node import WorkflowNodeModel
from workflow_platform.models.node_definition import NodeDefinitionModel


@dataclass
class NodeContext:
    execution: ExecutionModel
    node: WorkflowNodeModel
    node_execution: NodeExecutionModel
    node_definition: NodeDefinitionModel | None
    config: dict[str, Any]
    variables: dict[str, Any]
    ai_core: Any | None = None
    bridges: BridgeSet = field(default_factory=BridgeSet)
    extra: dict[str, Any] = field(default_factory=dict)
    """Engine-injected extras a handler occasionally needs but that don't
    belong on every context — e.g. the `repos` registry for handlers
    (APPROVAL) that need to write their own rows."""
