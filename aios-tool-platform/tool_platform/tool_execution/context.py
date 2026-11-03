"""ToolCallContext: everything a connector handler needs to do its job,
bundled so handler signatures stay uniform (`execute(ctx)`/`compensate(ctx)`)
regardless of what the connector actually does."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tool_platform.models.execution import ToolExecutionModel
from tool_platform.models.tool import ToolModel, ToolVersionModel


@dataclass
class ToolCallContext:
    tool: ToolModel
    tool_version: ToolVersionModel
    execution: ToolExecutionModel
    input_data: dict[str, Any]
    config: dict[str, Any]
    credential_secret: dict[str, Any] | None = None
    sandbox: Any | None = None
    network_policy: Any | None = None
    ai_core: Any | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    """Engine-injected extras a connector occasionally needs but that
    don't belong on every context — e.g. the `repos` registry."""
