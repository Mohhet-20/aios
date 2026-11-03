"""TaskOrchestrator: the intelligent orchestration layer — turns a
decomposed task tree into actual agent executions. Every strategy below
(sequential/parallel/hierarchical/consensus/supervisor/collaborative) is
built on the same two primitives: `AgentExecutor` (one agent "turn") and
the task's own lifecycle state machine (`domain.entities.Task`), so no
strategy reimplements execution bookkeeping — they differ only in *which*
tasks run against *which* agents in *what* order.

Interruptible execution and recovery-after-failure (explicitly in-scope
under ORCHESTRATION, unlike the full Workflow Engine) are implemented
here: a per-root-task `asyncio.Event` cancellation token checked at every
loop-iteration boundary, and `ExecutionCheckpointModel`-backed
checkpoint/recover.
"""
from __future__ import annotations

import asyncio
from collections import Counter


from ai_core.bootstrap import AICoreContext

from agent_platform.communication.communication_service import CommunicationService
from agent_platform.coordination.supervisor_decision import decide_next_step
from agent_platform.core.exceptions import ExecutionCancelledError, NotFoundError, OrchestrationError
from agent_platform.domain.enums import AgentLifecycleStatus, DelegationStatus, ExecutionStatus, TaskPriority, TaskStatus
from agent_platform.execution.agent_executor import AgentExecutor, ExecutionOutcome
from agent_platform.models.agent import AgentModel
from agent_platform.models.delegation import DelegationModel
from agent_platform.models.execution import ExecutionCheckpointModel
from agent_platform.models.task import TaskModel
from agent_platform.planner.mappers import apply_task_domain_to_model, task_to_domain
from agent_platform.planner.ordering import topological_order
from agent_platform.policies.approval_service import ApprovalService
from agent_platform.policies.policy_engine import PolicyEngine
from agent_platform.repositories.registry import RepositoryRegistry
from agent_platform.clock import utc_now


class TaskOrchestrator:
    def __init__(
        self, repos: RepositoryRegistry, ai_core: AICoreContext, *,
        communication: CommunicationService, executor: AgentExecutor | None = None, max_concurrency: int = 10,
        policy_engine: PolicyEngine | None = None, approval_service: ApprovalService | None = None,
    ):
        self.repos = repos
        self.ai_core = ai_core
        self.communication = communication
        self.executor = executor or AgentExecutor(repos, ai_core)
        self.max_concurrency = max_concurrency
        self.policy_engine = policy_engine
        self.approval_service = approval_service or ApprovalService(repos)
        self._cancellation_tokens: dict[str, asyncio.Event] = {}
        # AsyncSession (and the single DB connection behind it) is not safe for
        # concurrent use — parallel/consensus branches share one session, so their
        # session-touching work is serialized here even though the model calls
        # themselves are logically independent, concurrent units of work.
        self._session_lock = asyncio.Lock()

    # -- cancellation (interruptible execution) --------------------------------------

    def get_cancellation_token(self, root_task_id: str) -> asyncio.Event:
        return self._cancellation_tokens.setdefault(root_task_id, asyncio.Event())

    async def cancel(self, root_task_id: str, *, reason: str | None = None) -> None:
        self.get_cancellation_token(root_task_id).set()
        await self.communication.log_event(root_task_id, f"orchestration cancelled: {reason or 'requested'}")

    def _check_cancelled(self, root_task_id: str) -> None:
        if self.get_cancellation_token(root_task_id).is_set():
            raise ExecutionCancelledError(f"orchestration of root task '{root_task_id}' was cancelled")

    # -- routing (dynamic delegation / task routing / priority-aware load balancing) -

    async def route_task(self, task: TaskModel, candidates: list[AgentModel]) -> AgentModel:
        if not candidates:
            raise OrchestrationError(f"no candidate agents available to route task '{task.id}'")
        pool = [a for a in candidates if a.status == AgentLifecycleStatus.ACTIVE.value] or candidates
        scored = []
        for agent in pool:
            recent = await self.repos.executions.list_for_agent(agent.id, limit=50)
            active_load = sum(1 for e in recent if e.status == ExecutionStatus.RUNNING.value)
            success_rate = await self.repos.executions.success_rate(agent.id)
            scored.append((active_load, -success_rate, agent))
        scored.sort(key=lambda row: (row[0], row[1]))
        return scored[0][2]

    async def _resolve_agent(self, task: TaskModel, *, candidates: list[AgentModel] | None = None) -> AgentModel:
        if task.assigned_agent_id:
            return await self.repos.agents.get_or_404(task.assigned_agent_id)
        if candidates:
            return await self.route_task(task, candidates)
        raise OrchestrationError(f"task '{task.id}' has no assigned agent and no candidate agents were provided")

    # -- task-tree helpers -------------------------------------------------------------

    async def _ordered(self, root_task_id: str) -> tuple[dict[str, TaskModel], list[str], list[tuple[str, str]]]:
        subtasks = await self.repos.tasks.list_for_root(root_task_id)
        children = [t for t in subtasks if t.id != root_task_id]
        pool = children if children else subtasks  # a leaf goal with no decomposition executes as itself
        tasks_by_id = {t.id: t for t in pool}
        task_ids = list(tasks_by_id.keys())
        priorities = {tid: TaskPriority(t.priority) for tid, t in tasks_by_id.items()}
        all_edges = await self.repos.task_dependencies.all_edges_for_root([root_task_id])
        edges = [(a, b) for a, b in all_edges if a in tasks_by_id and b in tasks_by_id]
        order = topological_order(task_ids, edges, priorities)
        return tasks_by_id, order, edges

    @staticmethod
    def _dependencies_ok(task_id: str, tasks_by_id: dict[str, TaskModel], edges: list[tuple[str, str]]) -> bool:
        for task, depends_on in edges:
            if task == task_id and tasks_by_id[depends_on].status != TaskStatus.COMPLETED.value:
                return False
        return True

    # -- task lifecycle transitions (shared by every strategy) -------------------------

    async def _begin(self, task: TaskModel, agent: AgentModel) -> TaskModel:
        entity = task_to_domain(task)
        if entity.status == TaskStatus.FAILED:
            entity.retry()
        elif entity.status not in (TaskStatus.IN_PROGRESS,):
            entity.begin_execution(assigned_agent_id=agent.id)
        apply_task_domain_to_model(entity, task)
        return await self.repos.tasks.update(task)

    async def _complete(self, task: TaskModel, result: dict, *, confidence: float | None = None) -> TaskModel:
        entity = task_to_domain(task)
        entity.complete(result, confidence=confidence)
        apply_task_domain_to_model(entity, task)
        return await self.repos.tasks.update(task)

    async def _fail(self, task: TaskModel, reason: str) -> TaskModel:
        entity = task_to_domain(task)
        entity.fail(reason)
        apply_task_domain_to_model(entity, task)
        return await self.repos.tasks.update(task)

    async def _block(self, task: TaskModel, reason: str) -> TaskModel:
        entity = task_to_domain(task)
        if entity.status == TaskStatus.PENDING:
            entity.start_planning()
        entity.block(reason)
        apply_task_domain_to_model(entity, task)
        return await self.repos.tasks.update(task)

    async def _execute_task(
        self, task: TaskModel, agent: AgentModel, *, extra_context: str | None = None,
        cancellation_token: asyncio.Event | None = None, triggered_by: str | None = None,
    ) -> ExecutionOutcome:
        if self.policy_engine is not None:
            await self.policy_engine.check_resource_quota(agent)
            if self.policy_engine.requires_approval(agent, task):
                await self.approval_service.request_approval(
                    task, requested_by_agent_id=agent.id,
                    reason=f"agent '{agent.name}' requires approval before executing task '{task.title}'",
                )
                await self.communication.send_status_update(task.root_task_id, agent.id, f"task '{task.title}' is waiting for approval")
                return ExecutionOutcome(execution=None, response=None, success=False, error="approval_required")
        task = await self._begin(task, agent)
        await self.communication.send_status_update(task.root_task_id, agent.id, f"starting task '{task.title}'")
        outcome = await self.executor.run_with_retry(agent, task, cancellation_token=cancellation_token, extra_context=extra_context, triggered_by=triggered_by)
        if outcome.success:
            await self._complete(task, {"content": outcome.response.content, "execution_id": outcome.execution.id}, confidence=outcome.response.confidence)
            await self.communication.send_status_update(task.root_task_id, agent.id, f"completed task '{task.title}'")
        else:
            await self._fail(task, outcome.error or "execution failed")
            await self.communication.send_status_update(task.root_task_id, agent.id, f"failed task '{task.title}': {outcome.error}")
        return outcome

    # -- sequential execution (conditional routing via dependency-success gating) -----

    async def execute_sequential(self, root_task_id: str, agents: list[AgentModel], *, stop_on_failure: bool = True, triggered_by: str | None = None) -> dict:
        token = self.get_cancellation_token(root_task_id)
        tasks_by_id, order, edges = await self._ordered(root_task_id)
        results: dict[str, dict] = {}
        for task_id in order:
            self._check_cancelled(root_task_id)
            task = tasks_by_id[task_id]
            if not self._dependencies_ok(task_id, tasks_by_id, edges):
                await self._block(task, "upstream dependency failed")
                results[task_id] = {"status": "blocked"}
                if stop_on_failure:
                    break
                continue
            agent = await self._resolve_agent(task, candidates=agents)
            outcome = await self._execute_task(task, agent, cancellation_token=token, triggered_by=triggered_by)
            results[task_id] = {"status": "completed" if outcome.success else "failed", "error": outcome.error}
            if not outcome.success and stop_on_failure:
                break
        return results

    # -- parallel execution (wave-based, DAG-respecting, semaphore-bounded) -----------

    async def execute_parallel(self, root_task_id: str, agents: list[AgentModel], *, max_concurrency: int | None = None, triggered_by: str | None = None) -> dict:
        token = self.get_cancellation_token(root_task_id)
        tasks_by_id, order, edges = await self._ordered(root_task_id)
        remaining = set(order)
        completed_ids: set[str] = set()
        failed_ids: set[str] = set()
        results: dict[str, dict] = {}
        semaphore = asyncio.Semaphore(max_concurrency or self.max_concurrency)

        async def run_one(task_id: str) -> tuple[str, ExecutionOutcome]:
            async with semaphore, self._session_lock:
                task = tasks_by_id[task_id]
                agent = await self._resolve_agent(task, candidates=agents)
                return task_id, await self._execute_task(task, agent, cancellation_token=token, triggered_by=triggered_by)

        while remaining:
            self._check_cancelled(root_task_id)
            blocked_now = [tid for tid in remaining if any(dep in failed_ids for task, dep in edges if task == tid)]
            for task_id in blocked_now:
                await self._block(tasks_by_id[task_id], "upstream dependency failed")
                results[task_id] = {"status": "blocked"}
                remaining.discard(task_id)
            ready = [tid for tid in remaining if all(dep in completed_ids for task, dep in edges if task == tid)]
            if not ready:
                break  # nothing runnable and nothing newly blocked — guard against an infinite loop
            wave = await asyncio.gather(*(run_one(task_id) for task_id in ready))
            for task_id, outcome in wave:
                remaining.discard(task_id)
                if outcome.success:
                    completed_ids.add(task_id)
                    results[task_id] = {"status": "completed"}
                else:
                    failed_ids.add(task_id)
                    results[task_id] = {"status": "failed", "error": outcome.error}
        return results

    # -- delegation (direct handoff, recorded and inspectable) -------------------------

    async def delegate(self, task_id: str, from_agent_id: str | None, to_agent_id: str, *, reason: str | None = None) -> DelegationModel:
        task = await self.repos.tasks.get_or_404(task_id)
        to_agent = await self.repos.agents.get_or_404(to_agent_id)
        delegation = await self.repos.delegations.add(DelegationModel(
            task_id=task_id, from_agent_id=from_agent_id, to_agent_id=to_agent_id, reason=reason,
            status=DelegationStatus.PROPOSED.value,
        ))
        # v1 delegations auto-accept — no agent-side negotiation is modeled yet
        delegation.status = DelegationStatus.ACCEPTED.value
        delegation.accepted_at = utc_now()
        delegation = await self.repos.delegations.update(delegation)

        entity = task_to_domain(task)
        entity.assigned_agent_id = to_agent_id
        apply_task_domain_to_model(entity, task)
        await self.repos.tasks.update(task)

        await self.communication.send_handoff(task_id, from_agent_id, to_agent_id, reason or f"delegating task '{task.title}' to {to_agent.name}")
        return delegation

    # -- hierarchical execution (coordinator delegates every task to a chosen worker) -

    async def execute_hierarchical(self, root_task_id: str, coordinator: AgentModel, workers: list[AgentModel]) -> dict:
        token = self.get_cancellation_token(root_task_id)
        tasks_by_id, order, edges = await self._ordered(root_task_id)
        results: dict[str, dict] = {}
        for task_id in order:
            self._check_cancelled(root_task_id)
            task = tasks_by_id[task_id]
            if not self._dependencies_ok(task_id, tasks_by_id, edges):
                await self._block(task, "upstream dependency failed")
                results[task_id] = {"status": "blocked"}
                continue
            worker = await self.route_task(task, workers)
            await self.delegate(task_id, coordinator.id, worker.id, reason=f"coordinator delegating '{task.title}'")
            outcome = await self._execute_task(task, worker, cancellation_token=token)
            results[task_id] = {"status": "completed" if outcome.success else "failed", "error": outcome.error, "delegated_to": worker.id}
        return results

    # -- consensus-based execution (parallel independent attempts + majority vote) ----

    async def execute_consensus(self, task_id: str, agents: list[AgentModel], *, min_agreement: float = 0.34) -> dict:
        if len(agents) < 2:
            raise OrchestrationError("consensus execution requires at least two agents")
        task = await self.repos.tasks.get_or_404(task_id)
        token = self.get_cancellation_token(task.root_task_id)
        task = await self._begin(task, agents[0])

        async def _run_one(agent: AgentModel) -> ExecutionOutcome:
            async with self._session_lock:
                return await self.executor.run_with_retry(agent, task, cancellation_token=token)

        outcomes = await asyncio.gather(*(_run_one(agent) for agent in agents))
        successful = [(agent, outcome) for agent, outcome in zip(agents, outcomes) if outcome.success]
        if not successful:
            await self._fail(task, "all participating agents failed — no consensus possible")
            return {"status": "failed", "participants": len(agents), "successful": 0}

        normalized = [outcome.response.content.strip().lower() for _, outcome in successful]
        winning_text, winning_count = Counter(normalized).most_common(1)[0]
        agreement_ratio = winning_count / len(successful)
        winning_agent, winning_outcome = next(pair for pair in successful if pair[1].response.content.strip().lower() == winning_text)

        if agreement_ratio < min_agreement:
            await self._block(task, f"consensus not reached (agreement_ratio={agreement_ratio:.2f} < {min_agreement})")
            return {"status": "blocked", "agreement_ratio": agreement_ratio, "participants": len(agents), "successful": len(successful)}

        await self._complete(task, {"content": winning_outcome.response.content, "winning_agent_id": winning_agent.id}, confidence=agreement_ratio)
        return {
            "status": "completed", "agreement_ratio": agreement_ratio, "winning_agent_id": winning_agent.id,
            "participants": len(agents), "successful": len(successful),
        }

    # -- supervisor-controlled execution (a supervisor agent picks the next worker) ---

    async def execute_supervisor(self, root_task_id: str, supervisor: AgentModel, workers: list[AgentModel], *, max_rounds: int = 8) -> dict:
        if not workers:
            raise OrchestrationError("supervisor execution requires at least one worker agent")
        token = self.get_cancellation_token(root_task_id)
        root = await self.repos.tasks.get_or_404(root_task_id)
        root = await self._begin(root, supervisor)
        transcript: list[str] = []

        for round_num in range(max_rounds):
            self._check_cancelled(root_task_id)
            decision = await decide_next_step(
                self.ai_core, goal=root.goal,
                worker_descriptions=[{"id": w.id, "name": w.name, "role": w.role} for w in workers],
                conversation_summary="\n".join(transcript) or "(nothing has happened yet)",
            )
            if decision.is_complete:
                await self._complete(root, {"content": decision.final_result or "\n".join(transcript)})
                return {"status": "completed", "rounds": round_num + 1, "result": decision.final_result}

            worker = next((w for w in workers if w.id == decision.next_agent_id), workers[0])
            outcome = await self.executor.run_with_retry(worker, root, cancellation_token=token, extra_context=decision.instruction)
            line = f"[{worker.name}] instruction={decision.instruction!r} -> {'ok' if outcome.success else 'FAILED'}: " + (
                outcome.response.content if outcome.success else str(outcome.error)
            )
            transcript.append(line)
            await self.communication.send_status_update(root_task_id, worker.id, line)

        await self._fail(root, "supervisor did not reach completion within max_rounds")
        return {"status": "failed", "reason": "max_rounds_exceeded", "rounds": max_rounds}

    # -- collaborative execution (agents iteratively refine a shared blackboard draft) -

    async def execute_collaborative(self, root_task_id: str, agents: list[AgentModel], *, rounds: int = 3) -> dict:
        if not agents:
            raise OrchestrationError("collaborative execution requires at least one agent")
        token = self.get_cancellation_token(root_task_id)
        root = await self.repos.tasks.get_or_404(root_task_id)
        root = await self._begin(root, agents[0])
        draft = ""

        for round_num in range(rounds):
            for agent in agents:
                self._check_cancelled(root_task_id)
                extra = (
                    f"Current shared draft (refine and improve it — do not just repeat it):\n{draft}"
                    if draft else "No draft exists yet — produce the first version."
                )
                outcome = await self.executor.run_with_retry(agent, root, cancellation_token=token, extra_context=extra)
                if outcome.success:
                    draft = outcome.response.content
                    await self.communication.set_shared_value(root_task_id, "draft", {"content": draft, "updated_by": agent.id, "round": round_num}, updated_by=agent.id)
                    await self.communication.send_status_update(root_task_id, agent.id, f"round {round_num + 1}: updated shared draft")
                else:
                    await self.communication.send_status_update(root_task_id, agent.id, f"round {round_num + 1}: failed to contribute: {outcome.error}")

        if not draft:
            await self._fail(root, "no participating agent produced a usable draft")
            return {"status": "failed", "rounds": rounds}

        await self._complete(root, {"content": draft, "rounds": rounds, "contributors": [a.id for a in agents]})
        return {"status": "completed", "rounds": rounds, "content": draft}

    # -- checkpoint / recovery (recovery after failure) --------------------------------

    async def checkpoint(self, task_id: str, label: str, state: dict, *, agent_id: str | None = None) -> ExecutionCheckpointModel:
        return await self.repos.checkpoints.add(ExecutionCheckpointModel(task_id=task_id, agent_id=agent_id, label=label, state=state))

    async def recover(self, task_id: str) -> dict:
        checkpoint = await self.repos.checkpoints.latest_for_task(task_id)
        if checkpoint is None:
            raise NotFoundError(f"no checkpoint recorded for task '{task_id}' to recover from")
        task = await self.repos.tasks.get_or_404(task_id)
        entity = task_to_domain(task)
        if entity.status == TaskStatus.FAILED:
            entity.retry()
        elif entity.status == TaskStatus.WAITING_APPROVAL:
            entity.approve_and_resume()
        elif entity.status == TaskStatus.BLOCKED:
            entity.begin_execution()
        apply_task_domain_to_model(entity, task)
        task = await self.repos.tasks.update(task)
        self.get_cancellation_token(task.root_task_id).clear()
        return {"task_id": task.id, "status": task.status, "resumed_from_checkpoint": checkpoint.label, "state": checkpoint.state}
