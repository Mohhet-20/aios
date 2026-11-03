"""Tree-of-thought reasoning: explore several independent chain-of-thought
branches concurrently (each a separate structured-output call — logically
independent AI Core calls, not competing for a shared DB session, so real
concurrency here is safe unlike orchestration's DB-writing branches) and
select the highest-confidence branch as the answer. A v1, honest approach:
branch selection is by self-reported+attempt-based confidence, not a
separate arbiter/scoring model call — documented as a natural place to add
a real evaluator later without changing this function's contract.
"""
from __future__ import annotations

import asyncio

from ai_core.bootstrap import AICoreContext

from agent_platform.models.agent import AgentModel
from agent_platform.models.task import TaskModel
from agent_platform.reasoning.chain_of_thought import run_chain_of_thought
from agent_platform.reasoning.schemas import ChainOfThoughtResult


async def run_tree_of_thought(
    ai_core: AICoreContext, agent: AgentModel, task: TaskModel, *, branches: int = 3, max_steps: int = 4, extra_context: str | None = None,
) -> tuple[ChainOfThoughtResult, float, int]:
    if branches < 1:
        raise ValueError("tree-of-thought requires at least one branch")

    results = await asyncio.gather(*(
        run_chain_of_thought(ai_core, agent, task, max_steps=max_steps, extra_context=extra_context, temperature=0.7)
        for _ in range(branches)
    ))
    best_instance, best_confidence = max(results, key=lambda pair: pair[1])
    return best_instance, best_confidence, branches
