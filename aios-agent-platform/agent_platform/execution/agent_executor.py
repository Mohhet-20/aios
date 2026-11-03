"""AgentExecutor: the core "one agent turn" primitive every orchestration
strategy is built on — renders an agent's instructions + a task's goal
into a model call, executes it through the AI Core, and persists an
AgentExecutionModel row (success or failure) via Prompt-Platform-style
observability logging. Retries respect the agent's own `resource_limits`
(timeout_seconds) and are capped by the orchestrator's global settings,
not just the agent's own optimism.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass


from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.schemas.responses import GenerationResponse
from ai_core.utils.exceptions import AllProvidersFailedError

from agent_platform.core.exceptions import ExecutionCancelledError
from agent_platform.models.agent import AgentModel
from agent_platform.models.execution import AgentExecutionModel
from agent_platform.models.task import TaskModel
from agent_platform.repositories.registry import RepositoryRegistry
from agent_platform.tool_bridge.tool_bridge_service import ToolBridgeService
from agent_platform.clock import utc_now


@dataclass
class ExecutionOutcome:
    execution: AgentExecutionModel | None
    response: GenerationResponse | None
    success: bool
    error: str | None = None


class AgentExecutor:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext, *, observability=None, tool_bridge: ToolBridgeService | None = None):
        self.repos = repos
        self.ai_core = ai_core
        self.observability = observability  # optional ObservabilityService (Task 62); logs a mirror entry if provided
        self.tool_bridge = tool_bridge  # optional — when set, run() executes a real ReAct-style tool-calling loop

    def _build_request(self, agent: AgentModel, task: TaskModel, *, extra_context: str | None = None) -> GenerationRequest:
        config = agent.configuration or {}
        user_content = f"Task: {task.title}\nGoal: {task.goal}"
        if task.context:
            user_content += f"\n\nContext: {task.context}"
        if extra_context:
            user_content += f"\n\n{extra_context}"
        messages = [
            ChatMessage(role=Role.SYSTEM, content=agent.instructions),
            ChatMessage(role=Role.USER, content=user_content),
        ]
        return GenerationRequest(
            messages=messages, model=config.get("model"), provider=config.get("provider"),
            temperature=config.get("temperature", 0.7), max_tokens=config.get("max_tokens") or agent.context_window_override,
        )

    async def run(self, agent: AgentModel, task: TaskModel, *, triggered_by: str | None = None, extra_context: str | None = None) -> ExecutionOutcome:
        timeout = (agent.resource_limits or {}).get("timeout_seconds", 120.0)
        max_tool_rounds = int((agent.resource_limits or {}).get("max_tool_rounds", 3))
        base_request = self._build_request(agent, task, extra_context=extra_context)

        if self.tool_bridge is not None:
            tools = await self.tool_bridge.available_tools(agent.id)
            if tools:
                base_request = base_request.model_copy(update={"tools": tools})

        execution = AgentExecutionModel(agent_id=agent.id, task_id=task.id, triggered_by=triggered_by)
        execution = await self.repos.executions.add(execution)

        messages = list(base_request.messages)
        total_tool_calls = 0
        response: GenerationResponse | None = None

        try:
            round_num = 0
            while True:
                current_request = base_request.model_copy(update={"messages": messages})
                response = await asyncio.wait_for(self.ai_core.execution_engine.generate(current_request), timeout=timeout)

                has_capacity = round_num < max_tool_rounds
                if not (response.tool_calls and self.tool_bridge is not None and has_capacity):
                    break  # no tool calls requested, no bridge configured, or out of tool rounds — this response is final

                total_tool_calls += len(response.tool_calls)
                tool_results = await self.tool_bridge.invoke_many(agent.id, response.tool_calls)
                messages.append(ChatMessage(
                    role=Role.ASSISTANT, content=response.content,
                    tool_calls=[tc.model_dump() for tc in response.tool_calls],
                ))
                for tool_call, result in zip(response.tool_calls, tool_results):
                    content = result.error if result.is_error else result.content
                    messages.append(ChatMessage(role=Role.TOOL, tool_call_id=tool_call.id, name=tool_call.name, content=str(content)))
                round_num += 1
        except asyncio.TimeoutError:
            return await self._finalize_failure(execution, f"execution exceeded {timeout}s timeout")
        except AllProvidersFailedError as exc:
            return await self._finalize_failure(execution, str(exc))
        except Exception as exc:  # noqa: BLE001 — any model-call or tool-call failure is a recorded execution failure, not a crash
            return await self._finalize_failure(execution, str(exc))

        execution.status = "completed"
        execution.model_used = response.execution.model
        execution.provider_used = response.execution.provider
        execution.latency_ms = response.execution.latency_ms
        execution.input_tokens = response.usage.input_tokens
        execution.output_tokens = response.usage.output_tokens
        execution.cost_usd = response.cost.total_cost_usd
        execution.retry_count = response.execution.retries
        execution.tool_calls_count = total_tool_calls
        execution.success = True
        execution.completed_at = utc_now()
        execution = await self.repos.executions.update(execution)

        return ExecutionOutcome(execution=execution, response=response, success=True)

    async def _finalize_failure(self, execution: AgentExecutionModel, error: str) -> ExecutionOutcome:
        execution.status = "failed"
        execution.success = False
        execution.error_message = error
        execution.completed_at = utc_now()
        execution = await self.repos.executions.update(execution)
        return ExecutionOutcome(execution=execution, response=None, success=False, error=error)

    async def run_with_retry(
        self, agent: AgentModel, task: TaskModel, *, max_retries: int = 2, triggered_by: str | None = None,
        cancellation_token: asyncio.Event | None = None, extra_context: str | None = None,
    ) -> ExecutionOutcome:
        last_outcome: ExecutionOutcome | None = None
        for attempt in range(max_retries + 1):
            if cancellation_token is not None and cancellation_token.is_set():
                raise ExecutionCancelledError(f"Execution of task '{task.id}' was cancelled before attempt {attempt + 1}")
            outcome = await self.run(agent, task, triggered_by=triggered_by, extra_context=extra_context)
            if outcome.success:
                return outcome
            last_outcome = outcome
        return last_outcome
