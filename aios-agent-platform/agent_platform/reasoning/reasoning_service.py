"""ReasoningService: the facade the rest of the platform (and eventually
the Reasoning Viewer frontend surface) calls to make an agent think out
loud and get a persisted, inspectable ReasoningTraceModel back — dispatches
to chain-of-thought or tree-of-thought based on `mode`, but the caller
doesn't need to know which structured-output shape either one produces.
"""
from __future__ import annotations

from ai_core.bootstrap import AICoreContext

from agent_platform.domain.enums import ReasoningMode
from agent_platform.models.agent import AgentModel
from agent_platform.models.reasoning import ReasoningTraceModel
from agent_platform.models.task import TaskModel
from agent_platform.reasoning.chain_of_thought import run_chain_of_thought
from agent_platform.reasoning.tree_of_thought import run_tree_of_thought
from agent_platform.repositories.registry import RepositoryRegistry


class ReasoningService:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext):
        self.repos = repos
        self.ai_core = ai_core

    async def think(
        self, agent: AgentModel, task: TaskModel, *, mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHT,
        execution_id: str | None = None, branches: int = 3, max_steps: int = 5, extra_context: str | None = None,
    ) -> ReasoningTraceModel:
        if mode == ReasoningMode.TREE_OF_THOUGHT:
            instance, confidence, branches_explored = await run_tree_of_thought(
                self.ai_core, agent, task, branches=branches, max_steps=max_steps, extra_context=extra_context,
            )
        else:
            instance, confidence = await run_chain_of_thought(
                self.ai_core, agent, task, max_steps=max_steps, extra_context=extra_context,
            )
            branches_explored = 1

        trace = ReasoningTraceModel(
            execution_id=execution_id, task_id=task.id, agent_id=agent.id, mode=mode.value,
            steps=[step.model_dump() for step in instance.steps], branches_explored=branches_explored,
            final_answer=instance.final_answer, confidence=confidence,
        )
        return await self.repos.reasoning_traces.add(trace)

    async def get_trace(self, trace_id: str) -> ReasoningTraceModel:
        return await self.repos.reasoning_traces.get_or_404(trace_id)

    async def list_for_task(self, task_id: str) -> list[ReasoningTraceModel]:
        return await self.repos.reasoning_traces.list_for_task(task_id)

    async def list_for_execution(self, execution_id: str) -> list[ReasoningTraceModel]:
        return await self.repos.reasoning_traces.list_for_execution(execution_id)
