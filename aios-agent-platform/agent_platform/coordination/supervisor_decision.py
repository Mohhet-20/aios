"""Supervisor-controlled execution's decision step: the supervisor agent
looks at the task and conversation-so-far and decides which worker acts
next (or that the task is done), via structured output so the decision
is a typed object the orchestrator can act on directly rather than a
free-text response it has to parse.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.structured_output.engine import StructuredOutputEngine


class SupervisorDecision(BaseModel):
    is_complete: bool = Field(description="True if the task's goal has been fully achieved by the work so far")
    next_agent_id: str | None = Field(default=None, description="id of the worker agent that should act next; null if is_complete is true")
    instruction: str = Field(default="", description="What the next worker should specifically do")
    final_result: str | None = Field(default=None, description="The final answer, only set when is_complete is true")


async def decide_next_step(
    ai_core: AICoreContext, *, goal: str, worker_descriptions: list[dict], conversation_summary: str, temperature: float = 0.2,
) -> SupervisorDecision:
    workers_block = "\n".join(f"- id={w['id']}: {w['name']} ({w['role']})" for w in worker_descriptions)
    messages = [
        ChatMessage(role=Role.SYSTEM, content=(
            "You are a supervisor coordinating a team of specialist worker agents to accomplish a goal. "
            "Given the goal, the available workers, and what's happened so far, decide whether the goal is "
            "already achieved. If not, pick exactly one worker (by id) to act next and give them a precise instruction."
        )),
        ChatMessage(role=Role.USER, content=f"Goal: {goal}\n\nAvailable workers:\n{workers_block}\n\nProgress so far:\n{conversation_summary}"),
    ]
    request = GenerationRequest(messages=messages, temperature=temperature)
    engine = StructuredOutputEngine(ai_core.execution_engine)
    result = await engine.execute(request, SupervisorDecision)
    return result.instance
