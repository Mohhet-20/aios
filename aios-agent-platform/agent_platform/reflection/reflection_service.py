"""ReflectionService: the "did you check your work" half of the Reasoning
& Reflection engine — critique cycles, self-review/self-correction, and
verification-before-final-output, all backed by the same structured-output
CritiqueResult contract and persisted as ReflectionModel rows so a
critique cycle is inspectable after the fact (the Conversation Inspector /
Reasoning Viewer frontend surfaces read straight from these).

`run_reflection_loop` is where this actually changes behavior, not just
records it: it re-runs the worker agent with the prior critique injected
as extra context when verification fails, up to `max_iterations` times —
the self-correction loop the design calls for, built on the same
AgentExecutor primitive the orchestration engine uses, not a parallel
execution path.
"""
from __future__ import annotations

import asyncio

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.structured_output.engine import StructuredOutputEngine

from agent_platform.execution.agent_executor import AgentExecutor
from agent_platform.models.agent import AgentModel
from agent_platform.models.reasoning import ReflectionModel
from agent_platform.models.task import TaskModel
from agent_platform.reasoning.schemas import CritiqueResult
from agent_platform.repositories.registry import RepositoryRegistry


class ReflectionService:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext):
        self.repos = repos
        self.ai_core = ai_core

    async def critique(
        self, *, response_content: str, task: TaskModel, reflecting_agent: AgentModel, execution_id: str, iteration: int = 1,
    ) -> ReflectionModel:
        messages = [
            ChatMessage(role=Role.SYSTEM, content=(
                f"{reflecting_agent.instructions}\n\nYou are critiquing another agent's work. Be specific about any "
                "errors, omissions, or ways the response fails to fully satisfy the goal. Decide whether it passes."
            )),
            ChatMessage(role=Role.USER, content=f"Goal: {task.goal}\n\nResponse to critique:\n{response_content}"),
        ]
        request = GenerationRequest(messages=messages, temperature=0.2)
        engine = StructuredOutputEngine(self.ai_core.execution_engine)
        result = await engine.execute(request, CritiqueResult)
        instance = result.instance
        confidence = min(instance.confidence, result.confidence)

        reflection = ReflectionModel(
            execution_id=execution_id, task_id=task.id, reflecting_agent_id=reflecting_agent.id, iteration=iteration,
            critique=instance.critique, self_correction=instance.suggested_correction,
            passed_verification=instance.passed, confidence=confidence,
        )
        return await self.repos.reflections.add(reflection)

    async def verify_output(
        self, *, response_content: str, task: TaskModel, verifier_agent: AgentModel, execution_id: str, iteration: int = 1,
    ) -> ReflectionModel:
        """Semantic alias for `critique` for the "verification before final
        output" gate — same mechanism (a structured critique call), used
        specifically with a Verifier-type agent as the final check before a
        result is treated as done."""
        return await self.critique(
            response_content=response_content, task=task, reflecting_agent=verifier_agent,
            execution_id=execution_id, iteration=iteration,
        )

    async def run_reflection_loop(
        self, executor: AgentExecutor, worker_agent: AgentModel, task: TaskModel, *,
        critic_agent: AgentModel, max_iterations: int = 3, cancellation_token: asyncio.Event | None = None,
    ) -> dict:
        history: list[ReflectionModel] = []
        extra_context: str | None = None
        outcome = None

        for iteration in range(1, max_iterations + 1):
            outcome = await executor.run_with_retry(worker_agent, task, cancellation_token=cancellation_token, extra_context=extra_context)
            if not outcome.success:
                return {"status": "execution_failed", "iterations": iteration, "outcome": outcome, "reflections": history}

            reflection = await self.critique(
                response_content=outcome.response.content, task=task, reflecting_agent=critic_agent,
                execution_id=outcome.execution.id, iteration=iteration,
            )
            history.append(reflection)
            if reflection.passed_verification:
                return {"status": "passed", "iterations": iteration, "outcome": outcome, "reflections": history}

            extra_context = (
                f"Your previous attempt was reviewed and did not pass verification.\n"
                f"Critique: {reflection.critique}\n"
                f"Suggested correction: {reflection.self_correction or '(none given)'}\n"
                "Revise your response to fully address this feedback."
            )

        return {"status": "failed_verification", "iterations": max_iterations, "outcome": outcome, "reflections": history}

    async def list_for_execution(self, execution_id: str) -> list[ReflectionModel]:
        return await self.repos.reflections.list_for_execution(execution_id)

    async def list_for_task(self, task_id: str) -> list[ReflectionModel]:
        return await self.repos.reflections.list_for_task(task_id)
