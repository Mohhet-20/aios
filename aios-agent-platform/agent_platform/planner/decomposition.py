"""LLM-backed goal decomposition: turns a natural-language goal into a
structured, dependency-aware set of subtasks via the AI Core's
StructuredOutputEngine — the same repair-retry-validated pattern the
Prompt Platform's evaluation judge uses, so a malformed plan gets
re-prompted rather than silently accepted.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.structured_output.engine import StructuredOutputEngine

_PLANNER_SYSTEM_PROMPT = (
    "You are a planning specialist inside a multi-agent AI operating system. "
    "Decompose the given goal into the smallest set of concrete, independently-executable subtasks "
    "that together accomplish it. For each subtask, list the (zero-based) indices of any other "
    "subtasks in your list that must complete first (its dependencies) — most subtasks have none. "
    "Do not create more subtasks than necessary."
)


class SubtaskPlan(BaseModel):
    title: str = Field(description="Short imperative title, e.g. 'Research competitor pricing'")
    goal: str = Field(description="One or two sentences describing exactly what done looks like")
    priority: str = Field(default="normal", description="One of: low, normal, high, critical")
    depends_on: list[int] = Field(default_factory=list, description="Zero-based indices of prerequisite subtasks in this same list")
    estimated_tokens: int = Field(default=2000, ge=0)
    estimated_duration_seconds: float = Field(default=60.0, ge=0)


class DecompositionPlan(BaseModel):
    rationale: str = Field(description="Brief explanation of the decomposition strategy")
    subtasks: list[SubtaskPlan]


async def decompose_goal(
    ai_core: AICoreContext, goal: str, *, context: dict | None = None, max_subtasks: int = 8, temperature: float = 0.2,
) -> DecompositionPlan:
    context_block = f"\n\nAdditional context:\n{context}" if context else ""
    messages = [
        ChatMessage(role=Role.SYSTEM, content=f"{_PLANNER_SYSTEM_PROMPT} Produce at most {max_subtasks} subtasks."),
        ChatMessage(role=Role.USER, content=f"Goal: {goal}{context_block}"),
    ]
    request = GenerationRequest(messages=messages, temperature=temperature)
    engine = StructuredOutputEngine(ai_core.execution_engine)
    result = await engine.execute(request, DecompositionPlan)
    plan = result.instance
    if len(plan.subtasks) > max_subtasks:
        plan.subtasks = plan.subtasks[:max_subtasks]
    return plan
