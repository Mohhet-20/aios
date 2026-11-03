"""Agent aggregate — a specialized AI worker scoped to a workspace, a model
preference, an allowed tool list, and a memory scope, per the Agent Engine
design in Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.value_objects.enums import AgentStatus


@dataclass
class Agent:
    id: str
    workspace_id: str
    name: str
    role: str
    description: str
    model_id: str
    allowed_tool_ids: list[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    runs_today: int = 0
    success_rate: float = 0.0

    def is_permitted_tool(self, tool_id: str) -> bool:
        """Enforces the Tool Engine's permission-scoping rule from Phase 1:
        an agent may only invoke tools explicitly in its allowlist."""
        return tool_id in self.allowed_tool_ids
