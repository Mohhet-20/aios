"""Plain-dataclass shapes for a tool plan — no ORM, no persistence (a
plan is a transient planning artifact an agent/workflow acts on
immediately, not a durable record the way a Tool or Execution is)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RankedTool:
    tool_id: str
    name: str
    category: str
    score: float
    reason: str


@dataclass
class PlanStep:
    step_id: str
    tool_id: str
    input_template: dict[str, Any]
    """Values may reference a prior step's output with the string
    `"$steps.<step_id>.<field>"` — resolved against accumulated step
    outputs at execution time by `resolve_step_input`."""


@dataclass
class ToolPlan:
    steps: list[PlanStep] = field(default_factory=list)

    def add_step(self, step_id: str, tool_id: str, input_template: dict[str, Any]) -> PlanStep:
        step = PlanStep(step_id=step_id, tool_id=tool_id, input_template=input_template)
        self.steps.append(step)
        return step
