"""Chain-of-thought reasoning: one structured-output call that asks the
model to lay out discrete thought/action/observation steps before
committing to a final answer, with a confidence estimate that combines
the model's own self-reported confidence with the StructuredOutputEngine's
attempt-based confidence (a response that needed a repair round is less
trustworthy than one that validated on the first try, regardless of what
the model itself claims) — deliberately conservative, taking the min.
"""
from __future__ import annotations

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.structured_output.engine import StructuredOutputEngine

from agent_platform.models.agent import AgentModel
from agent_platform.models.task import TaskModel
from agent_platform.reasoning.schemas import ChainOfThoughtResult


async def run_chain_of_thought(
    ai_core: AICoreContext, agent: AgentModel, task: TaskModel, *, max_steps: int = 5, extra_context: str | None = None, temperature: float = 0.3,
) -> tuple[ChainOfThoughtResult, float]:
    system = (
        f"{agent.instructions}\n\nThink step by step before answering. Break your reasoning into at most "
        f"{max_steps} discrete steps, each with a thought and — if you took an action — what you did and "
        f"what you observed. Then give a single final answer and your confidence in it."
    )
    user_content = f"Task: {task.title}\nGoal: {task.goal}"
    if task.context:
        user_content += f"\n\nContext: {task.context}"
    if extra_context:
        user_content += f"\n\n{extra_context}"

    messages = [ChatMessage(role=Role.SYSTEM, content=system), ChatMessage(role=Role.USER, content=user_content)]
    request = GenerationRequest(messages=messages, temperature=temperature)
    engine = StructuredOutputEngine(ai_core.execution_engine)
    result = await engine.execute(request, ChainOfThoughtResult)

    instance = result.instance
    combined_confidence = min(instance.confidence, result.confidence)
    return instance, combined_confidence
