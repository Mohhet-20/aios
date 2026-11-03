"""ExecutionEngine: the graph-walking core of the Workflow Orchestration
Engine. One `run()` call drives an execution from wherever it currently
sits (PENDING, or a checkpointed mid-graph position after a pause/resume)
until it either finishes (COMPLETED/FAILED/CANCELLED/COMPENSATED) or
hits a real pause point (WAITING_APPROVAL, WAIT, or a caller-issued
`pause_execution`).

Routing rules (enforced at publish time by `graph_validator`, relied on
here): every node has at most one outgoing edge, except CONDITION/
DECISION (branch on `evaluate_expression`), PARALLEL_BRANCH (fan out to
every outgoing edge concurrently via `asyncio.gather`, rejoining at the
paired MERGE), and LOOP (repeats its body up to `max_iterations` times,
or while a `condition` expression holds, or once per item in an `over`
collection).

This is a single-process, in-memory orchestration loop — "parallel"
here means real concurrent `asyncio` I/O (several LLM/API calls in
flight at once), not multi-process/distributed execution. Horizontal
scaling is achieved by running many `ExecutionEngine` workers against
the same database, each picking up different executions (see the
Scheduler in Task 89 and the self-review in Task 97 for how that's meant
to compose) — not by this class internally sharding one execution
across processes.

A single `AsyncSession` (and therefore a single `RepositoryRegistry`) is
never safe to touch from more than one coroutine at once, so PARALLEL_
BRANCH's concurrency is scoped carefully: `handler.execute()` calls (the
actual I/O-bound work — an LLM call, a REST call) run genuinely
concurrently via `asyncio.gather`, but every read/write through `repos`
is serialized behind `self._session_lock`. Node definitions are also
prefetched once per `run()` call rather than looked up mid-branch, so a
branch's only lock-guarded work is its own bookkeeping, not a redundant
SELECT every other branch is also trying to run.
"""
from __future__ import annotations

import asyncio
from typing import Any

from workflow_platform.ai_bridges.interfaces import BridgeSet
from workflow_platform.core.exceptions import (
    NodeExecutionError,
    RecursionLimitExceededError,
    ValidationError,
)
from workflow_platform.domain.enums import EventType, ExecutionStatus, NodeExecutionStatus, NodeType
from workflow_platform.models.checkpoint import CheckpointModel
from workflow_platform.models.execution import ExecutionModel, NodeExecutionModel
from workflow_platform.models.observability import ExecutionLogModel
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.workflow_engine.context import NodeContext
from workflow_platform.workflow_engine.expressions import evaluate_expression
from workflow_platform.workflow_engine.mappers import (
    apply_execution_domain_to_model,
    apply_node_execution_domain_to_model,
    execution_to_domain,
    node_execution_to_domain,
)
from workflow_platform.workflow_engine.registry import HandlerRegistry

_LOOP_COUNTER_PREFIX = "__loop_iter__"


class ExecutionEngine:
    def __init__(
        self,
        repos: RepositoryRegistry,
        handler_registry: HandlerRegistry,
        *,
        ai_core: Any | None = None,
        bridges: BridgeSet | None = None,
        max_recursion_depth: int = 10,
        sleep_fn=asyncio.sleep,
        event_bus=None,
        event_publisher=None,
        query_executor=None,
        approval_policy=None,
    ):
        self.repos = repos
        self.handlers = handler_registry
        self.ai_core = ai_core
        self.bridges = bridges or BridgeSet()
        self.max_recursion_depth = max_recursion_depth
        self._sleep = sleep_fn
        self.event_bus = event_bus
        publisher = event_bus.publish if event_bus is not None else event_publisher
        self._extra = {
            "repos": repos, "event_publisher": publisher, "query_executor": query_executor,
            "approval_policy": approval_policy,
        }
        self._session_lock = asyncio.Lock()

    async def _publish_workflow_event(self, execution: ExecutionModel, event_type: str, **extra_payload) -> None:
        if self.event_bus is None:
            return
        await self.event_bus.publish(
            event_type=event_type, workspace_id=execution.workspace_id, source_type="execution",
            source_id=execution.id, payload={"workflow_id": execution.workflow_id, **extra_payload},
        )

    # -- starting a run ---------------------------------------------------------

    async def start_execution(
        self, workflow_id: str, *, triggered_by: str | None = None, trigger_type: str = "manual",
        input_variables: dict | None = None, priority: str = "normal", parent_execution_id: str | None = None,
        recursion_depth: int = 0,
    ) -> ExecutionModel:
        if recursion_depth > self.max_recursion_depth:
            raise RecursionLimitExceededError(
                f"nested workflow invocation exceeded max recursion depth ({self.max_recursion_depth})"
            )

        async with self._session_lock:
            workflow = await self.repos.workflows.get_or_404(workflow_id)
            if not workflow.current_version_id:
                raise ValidationError(f"workflow '{workflow_id}' has no published version to execute")

            execution = await self.repos.executions.add(ExecutionModel(
                workflow_id=workflow_id, workflow_version_id=workflow.current_version_id, workspace_id=workflow.workspace_id,
                priority=priority, trigger_type=trigger_type, triggered_by=triggered_by,
                input_variables=input_variables or {}, context_variables=dict(input_variables or {}),
                parent_execution_id=parent_execution_id, recursion_depth=recursion_depth,
            ))
        return await self.run(execution.id)

    # -- the run loop -------------------------------------------------------------

    async def run(self, execution_id: str) -> ExecutionModel:
        just_started = False
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            nodes, edges = await self._load_graph(execution.workflow_version_id)
            node_defs_by_key = {d.key: d for d in await self.repos.node_definitions.list_all()}

            if entity.status == ExecutionStatus.PENDING:
                entity.start()
                start_node = next(n for n in nodes if n.node_type == NodeType.START.value)
                entity.current_node_key = start_node.node_key
                apply_execution_domain_to_model(entity, execution)
                execution = await self.repos.executions.update(execution)
                just_started = True

            if entity.status != ExecutionStatus.RUNNING:
                return execution  # nothing to drive (already terminal, paused, or waiting)

        if just_started:
            await self._publish_workflow_event(execution, EventType.WORKFLOW_STARTED.value)

        nodes_by_key = {n.node_key: n for n in nodes}
        outgoing_by_key: dict[str, list] = {}
        for e in edges:
            outgoing_by_key.setdefault(e.source_node_key, []).append(e)

        current_key = execution.current_node_key
        while current_key is not None:
            node = nodes_by_key[current_key]

            if node.node_type == NodeType.PARALLEL_BRANCH.value:
                next_key, should_stop = await self._run_parallel_branch(execution, node, nodes_by_key, outgoing_by_key, node_defs_by_key)
            else:
                next_key, should_stop = await self._run_single_node(execution, node, outgoing_by_key, node_defs_by_key)

            async with self._session_lock:
                execution = await self.repos.executions.get_or_404(execution.id)
            if should_stop:
                return execution
            current_key = next_key

        # ran off the end of the graph (reached a node with no outgoing edge, i.e. END)
        just_completed = False
        async with self._session_lock:
            entity = execution_to_domain(execution)
            if not entity.is_terminal():
                entity.complete(output_variables=dict(execution.context_variables))
                apply_execution_domain_to_model(entity, execution)
                execution = await self.repos.executions.update(execution)
                just_completed = True
        if just_completed:
            await self._publish_workflow_event(execution, EventType.WORKFLOW_COMPLETED.value)
        return execution

    async def _load_graph(self, version_id: str):
        return await self.repos.workflow_nodes.list_for_version(version_id), await self.repos.workflow_edges.list_for_version(version_id)

    # -- single-node dispatch -----------------------------------------------------

    async def _run_single_node(self, execution: ExecutionModel, node, outgoing_by_key: dict, node_defs_by_key: dict) -> tuple[str | None, bool]:
        """Returns (next_node_key_or_None, should_stop_run_loop)."""
        node_def = node_defs_by_key.get(node.node_type)

        if node.node_type == NodeType.LOOP.value:
            return await self._advance_loop(execution, node, outgoing_by_key)

        invoke_workflow_id = (node.config or {}).get("invoke_workflow_id")
        if invoke_workflow_id:
            return await self._run_nested_workflow(execution, node, invoke_workflow_id, outgoing_by_key)

        node_execution = await self._dispatch_node(execution, node, node_def)

        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution.id)

        if node_execution.status == NodeExecutionStatus.WAITING_APPROVAL.value:
            async with self._session_lock:
                entity = execution_to_domain(execution)
                entity.request_approval()
                apply_execution_domain_to_model(entity, execution)
                await self.repos.executions.update(execution)
            return None, True

        if node_execution.status != NodeExecutionStatus.SUCCEEDED.value:
            await self._handle_node_failure(execution, node_execution.error_message or "node failed")
            return None, True

        if node.node_type in (NodeType.CONDITION.value, NodeType.DECISION.value):
            next_key = self._select_branch(node, node_execution, outgoing_by_key.get(node.node_key, []))
        else:
            edges = outgoing_by_key.get(node.node_key, [])
            next_key = edges[0].target_node_key if edges else None

        async with self._session_lock:
            await self._advance_to(execution, next_key)
        return next_key, False

    async def _dispatch_node(self, execution: ExecutionModel, node, node_def) -> NodeExecutionModel:
        config = {**(node_def.default_config if node_def else {}), **(node.config or {})}
        timeout_seconds = node.timeout_seconds or (node_def.default_timeout_seconds if node_def else 300)
        max_retries = node.max_retries if node.max_retries is not None else (node_def.default_max_retries if node_def else 0)
        backoff = node_def.default_retry_backoff_seconds if node_def else 2.0

        async with self._session_lock:
            node_execution = await self.repos.node_executions.add(NodeExecutionModel(
                execution_id=execution.id, node_key=node.node_key, node_type=node.node_type,
                status=NodeExecutionStatus.PENDING.value, input_data=dict(execution.context_variables),
            ))
        ne_entity = node_execution_to_domain(node_execution)

        attempt = 0
        last_error: str | None = None
        while True:
            attempt += 1
            if ne_entity.status == NodeExecutionStatus.PENDING:
                ne_entity.start()
            else:
                ne_entity.resume_after_retry()
            async with self._session_lock:
                apply_node_execution_domain_to_model(ne_entity, node_execution)
                await self.repos.node_executions.update(node_execution)

            handler = self.handlers.get(node.node_type)
            ctx = NodeContext(
                execution=execution, node=node, node_execution=node_execution, node_definition=node_def,
                config=config, variables=execution.context_variables, ai_core=self.ai_core, bridges=self.bridges,
                extra=self._extra,
            )
            try:
                output = await asyncio.wait_for(handler.execute(ctx), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                last_error = f"node '{node.node_key}' timed out after {timeout_seconds}s"
                ne_entity.timeout(last_error)
            except NodeExecutionError as exc:
                last_error = str(exc)
                ne_entity.fail(last_error)
            except Exception as exc:  # noqa: BLE001 — any handler bug still needs to become a recorded failure
                last_error = f"{type(exc).__name__}: {exc}"
                ne_entity.fail(last_error)
            else:
                async with self._session_lock:
                    if node.node_type == NodeType.APPROVAL.value:
                        ne_entity.output_data = output
                        ne_entity.wait_for_approval()
                        apply_node_execution_domain_to_model(ne_entity, node_execution)
                        await self.repos.node_executions.update(node_execution)
                        return node_execution

                    ne_entity.succeed(output)
                    apply_node_execution_domain_to_model(ne_entity, node_execution)
                    node_execution = await self.repos.node_executions.update(node_execution)
                    execution.context_variables = {**execution.context_variables, **output}
                    await self.repos.executions.update(execution)
                    await self._checkpoint(execution, node.node_key)
                    await self._log(execution, node_execution, "info", f"node '{node.node_key}' succeeded in {ne_entity.duration_ms or 0:.1f}ms")
                    return node_execution

            async with self._session_lock:
                apply_node_execution_domain_to_model(ne_entity, node_execution)
                await self.repos.node_executions.update(node_execution)

                if attempt > max_retries:
                    # already FAILED/TIMED_OUT from the fail()/timeout() call above —
                    # that *is* the terminal state for this node execution.
                    execution.context_variables = {**execution.context_variables, "__last_error__": last_error}
                    await self.repos.executions.update(execution)
                    await self._log(execution, node_execution, "error", f"node '{node.node_key}' failed permanently after {attempt} attempt(s): {last_error}")
                    return node_execution

                ne_entity.retry()
                apply_node_execution_domain_to_model(ne_entity, node_execution)
                await self.repos.node_executions.update(node_execution)
                await self._log(execution, node_execution, "warning", f"node '{node.node_key}' failed (attempt {attempt}), retrying: {last_error}")
            await self._sleep(backoff * (2 ** (attempt - 1)))

    def _select_branch(self, node, node_execution: NodeExecutionModel, edges: list) -> str | None:
        branch_value = node_execution.output_data.get("branch_value")
        default_edge = None
        for edge in edges:
            condition = edge.condition or {}
            if "default" in condition:
                default_edge = edge
                continue
            if "when" in condition and condition["when"] == branch_value:
                return edge.target_node_key
            if "case" in condition and condition["case"] == branch_value:
                return edge.target_node_key
        if default_edge is not None:
            return default_edge.target_node_key
        raise NodeExecutionError(f"node '{node.node_key}' produced branch value {branch_value!r} matching no outgoing edge")

    async def _advance_to(self, execution: ExecutionModel, next_node_key: str | None) -> None:
        """Caller must already hold `self._session_lock`."""
        execution.current_node_key = next_node_key
        await self.repos.executions.update(execution)

    # -- nested / recursive workflow invocation --------------------------------------

    async def _run_nested_workflow(self, execution: ExecutionModel, node, sub_workflow_id: str, outgoing_by_key: dict) -> tuple[str | None, bool]:
        """A node whose config carries `invoke_workflow_id` triggers a full
        recursive `start_execution` call against another workflow (or the
        same one — recursion is legal, guarded by `max_recursion_depth`),
        sharing this engine's session. The child's `output_variables`
        become this node's output, merged into the parent's context
        exactly like any other node's output would be."""
        async with self._session_lock:
            node_execution = await self.repos.node_executions.add(NodeExecutionModel(
                execution_id=execution.id, node_key=node.node_key, node_type=node.node_type,
                status=NodeExecutionStatus.PENDING.value, input_data=dict(execution.context_variables),
            ))
            ne_entity = node_execution_to_domain(node_execution)
            ne_entity.start()
            apply_node_execution_domain_to_model(ne_entity, node_execution)
            await self.repos.node_executions.update(node_execution)

        error_message: str | None = None
        sub_execution = None
        try:
            sub_execution = await self.start_execution(
                sub_workflow_id, triggered_by=execution.triggered_by, trigger_type="event",
                input_variables=dict(execution.context_variables), parent_execution_id=execution.id,
                recursion_depth=execution.recursion_depth + 1,
            )
            if sub_execution.status != ExecutionStatus.COMPLETED.value:
                error_message = f"nested workflow execution '{sub_execution.id}' ended with status {sub_execution.status}"
        except RecursionLimitExceededError as exc:
            error_message = str(exc)

        next_key: str | None = None
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution.id)
            if error_message is None:
                ne_entity.succeed(dict(sub_execution.output_variables))
                apply_node_execution_domain_to_model(ne_entity, node_execution)
                await self.repos.node_executions.update(node_execution)
                execution.context_variables = {**execution.context_variables, **sub_execution.output_variables}
                await self.repos.executions.update(execution)
                await self._checkpoint(execution, node.node_key)
                edges = outgoing_by_key.get(node.node_key, [])
                next_key = edges[0].target_node_key if edges else None
                await self._advance_to(execution, next_key)
            else:
                ne_entity.fail(error_message)
                apply_node_execution_domain_to_model(ne_entity, node_execution)
                await self.repos.node_executions.update(node_execution)

        if error_message is not None:
            await self._handle_node_failure(execution, error_message)
            return None, True
        return next_key, False

    # -- PARALLEL_BRANCH / MERGE ---------------------------------------------------

    async def _run_parallel_branch(
        self, execution: ExecutionModel, node, nodes_by_key: dict, outgoing_by_key: dict, node_defs_by_key: dict
    ) -> tuple[str | None, bool]:
        branch_edges = outgoing_by_key.get(node.node_key, [])

        async def walk_branch(start_key: str):
            key = start_key
            while True:
                n = nodes_by_key[key]
                if n.node_type in (NodeType.MERGE.value, NodeType.END.value):
                    return key
                node_execution = await self._dispatch_node(execution, n, node_defs_by_key.get(n.node_type))
                if node_execution.status != NodeExecutionStatus.SUCCEEDED.value:
                    raise NodeExecutionError(f"branch node '{n.node_key}' failed: {node_execution.error_message}")
                edges = outgoing_by_key.get(key, [])
                if not edges:
                    return key
                key = edges[0].target_node_key

        try:
            terminal_keys = await asyncio.gather(*(walk_branch(e.target_node_key) for e in branch_edges))
        except NodeExecutionError as exc:
            async with self._session_lock:
                execution = await self.repos.executions.get_or_404(execution.id)
            await self._handle_node_failure(execution, str(exc))
            return None, True

        merge_candidates = {k for k in terminal_keys if nodes_by_key[k].node_type == NodeType.MERGE.value}
        end_candidates = {k for k in terminal_keys if nodes_by_key[k].node_type == NodeType.END.value}

        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution.id)

        if merge_candidates:
            merge_key = next(iter(merge_candidates))
            merge_node = nodes_by_key[merge_key]
            merge_node_execution = await self._dispatch_node(execution, merge_node, node_defs_by_key.get(merge_node.node_type))
            if merge_node_execution.status != NodeExecutionStatus.SUCCEEDED.value:
                await self._handle_node_failure(execution, merge_node_execution.error_message or "merge failed")
                return None, True
            edges = outgoing_by_key.get(merge_key, [])
            next_key = edges[0].target_node_key if edges else None
            async with self._session_lock:
                await self._advance_to(execution, next_key)
            return next_key, False

        if end_candidates:
            async with self._session_lock:
                await self._advance_to(execution, None)
            return None, False

        raise NodeExecutionError(f"PARALLEL_BRANCH '{node.node_key}' branches did not converge on a MERGE or END node")

    # -- LOOP -----------------------------------------------------------------------

    async def _advance_loop(self, execution: ExecutionModel, node, outgoing_by_key: dict) -> tuple[str | None, bool]:
        edges = outgoing_by_key.get(node.node_key, [])
        body_edge = next((e for e in edges if (e.condition or {}).get("loop_body")), None)
        exit_edge = next((e for e in edges if (e.condition or {}).get("loop_exit")), None)
        if body_edge is None or exit_edge is None:
            raise ValidationError(f"LOOP node '{node.node_key}' must have one loop_body edge and one loop_exit edge")

        counter_key = f"{_LOOP_COUNTER_PREFIX}{node.node_key}"
        iteration = execution.context_variables.get(counter_key, 0)
        max_iterations = node.config.get("max_iterations", 1000)

        collection = None
        over_var = node.config.get("over")
        if over_var:
            collection = execution.context_variables.get(over_var, [])

        condition_expr = node.config.get("condition")
        keep_looping = iteration < max_iterations
        if keep_looping and collection is not None:
            keep_looping = iteration < len(collection)
        if keep_looping and condition_expr:
            keep_looping = bool(evaluate_expression(condition_expr, execution.context_variables))

        async with self._session_lock:
            if not keep_looping:
                execution.context_variables = {k: v for k, v in execution.context_variables.items() if k != counter_key}
                await self.repos.executions.update(execution)
                await self._advance_to(execution, exit_edge.target_node_key)
                return exit_edge.target_node_key, False

            item_variable = node.config.get("item_variable", "item")
            updates = {counter_key: iteration + 1}
            if collection is not None:
                updates[item_variable] = collection[iteration]
            execution.context_variables = {**execution.context_variables, **updates}
            await self.repos.executions.update(execution)
            await self._checkpoint(execution, node.node_key)
            await self._advance_to(execution, body_edge.target_node_key)
            return body_edge.target_node_key, False

    # -- observability: structured execution logs (Task 93 reads these) ------------

    async def _log(self, execution: ExecutionModel, node_execution: NodeExecutionModel | None, level: str, message: str) -> None:
        """Caller must already hold `self._session_lock`."""
        await self.repos.execution_logs.add(ExecutionLogModel(
            execution_id=execution.id, node_execution_id=node_execution.id if node_execution else None,
            level=level, message=message,
        ))

    # -- checkpointing --------------------------------------------------------------

    async def _checkpoint(self, execution: ExecutionModel, node_key: str) -> None:
        """Caller must already hold `self._session_lock`."""
        latest = await self.repos.checkpoints.get_latest_for_execution(execution.id)
        sequence_number = (latest.sequence_number + 1) if latest else 1
        await self.repos.checkpoints.add(CheckpointModel(
            execution_id=execution.id, node_key=node_key, sequence_number=sequence_number,
            state_snapshot={"context_variables": dict(execution.context_variables), "current_node_key": execution.current_node_key},
        ))

    # -- failure / compensation -------------------------------------------------------

    async def _handle_node_failure(self, execution: ExecutionModel, error_message: str) -> None:
        async with self._session_lock:
            entity = execution_to_domain(execution)
            entity.fail(error_message)
            apply_execution_domain_to_model(entity, execution)
            execution = await self.repos.executions.update(execution)
        await self._publish_workflow_event(execution, EventType.WORKFLOW_FAILED.value, error_message=error_message)
        await self.rollback(execution.id)

    async def rollback(self, execution_id: str) -> ExecutionModel:
        """Saga-style compensation: walk every SUCCEEDED node_execution for
        this run, most-recent-first, and call `compensate()` on any whose
        node type is marked `is_compensable` on its `NodeDefinitionModel`.
        Compensation handlers themselves run outside the session lock
        (they may do their own I/O, e.g. an outbound HTTP undo call), but
        every repository read feeding them is lock-guarded."""
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            if entity.status not in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT):
                return execution

            entity.begin_compensation()
            apply_execution_domain_to_model(entity, execution)
            execution = await self.repos.executions.update(execution)

            node_executions = await self.repos.node_executions.list_for_execution(execution_id)
            node_defs_by_key = {d.key: d for d in await self.repos.node_definitions.list_all()}
            nodes_by_key = {n.node_key: n for n in await self.repos.workflow_nodes.list_for_version(execution.workflow_version_id)}

        succeeded = [ne for ne in node_executions if ne.status == NodeExecutionStatus.SUCCEEDED.value]
        succeeded.sort(key=lambda ne: ne.completed_at or ne.started_at, reverse=True)

        compensation_error: str | None = None
        for ne in succeeded:
            node_def = node_defs_by_key.get(ne.node_type)
            if node_def is None or not node_def.is_compensable:
                continue
            node = nodes_by_key.get(ne.node_key)
            if node is None:
                continue
            handler = self.handlers.get(ne.node_type)
            ctx = NodeContext(
                execution=execution, node=node, node_execution=ne, node_definition=node_def,
                config={**(node_def.default_config or {}), **(node.config or {})}, variables=execution.context_variables,
                ai_core=self.ai_core, bridges=self.bridges, extra=self._extra,
            )
            try:
                await handler.compensate(ctx)
            except Exception as exc:  # noqa: BLE001
                compensation_error = f"compensation of node '{ne.node_key}' failed: {exc}"
                break

        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            if compensation_error:
                entity.compensation_failed(compensation_error)
            else:
                entity.complete_compensation()
            apply_execution_domain_to_model(entity, execution)
            return await self.repos.executions.update(execution)

    # -- pause / resume / cancel / retry --------------------------------------------

    async def pause_execution(self, execution_id: str) -> ExecutionModel:
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            entity.pause()
            apply_execution_domain_to_model(entity, execution)
            return await self.repos.executions.update(execution)

    async def resume_execution(self, execution_id: str) -> ExecutionModel:
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            entity.resume()
            apply_execution_domain_to_model(entity, execution)
            await self.repos.executions.update(execution)
        return await self.run(execution_id)

    async def cancel_execution(self, execution_id: str) -> ExecutionModel:
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            entity.cancel()
            apply_execution_domain_to_model(entity, execution)
            execution = await self.repos.executions.update(execution)
        await self._publish_workflow_event(execution, EventType.WORKFLOW_CANCELLED.value)
        return execution

    async def resume_after_approval(self, execution_id: str, *, approved: bool, output_data: dict | None = None) -> ExecutionModel:
        """The counterpart to the APPROVAL node handler pausing a run:
        `ApprovalService` calls this once a human has decided. Unlike
        `resume_execution` (which just flips PAUSED->RUNNING and re-enters
        `run()` at whatever `current_node_key` already was), this method
        also finishes the node_execution that's WAITING_APPROVAL — marking
        it SUCCEEDED (approved) or SKIPPED (rejected, per the domain
        entity's `resume_after_approval`) — and advances `current_node_key`
        to that node's outgoing edge, since re-entering `run()` at the
        approval node itself would just re-dispatch it and create a
        duplicate approval request."""
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            node_executions = await self.repos.node_executions.list_for_execution(execution_id)
            node_execution = next(
                (ne for ne in node_executions if ne.status == NodeExecutionStatus.WAITING_APPROVAL.value), None
            )
            if node_execution is None:
                raise ValidationError(f"execution '{execution_id}' has no node currently awaiting approval")

            ne_entity = node_execution_to_domain(node_execution)
            ne_entity.resume_after_approval(approved=approved)
            merged_output = {**ne_entity.output_data, "approved": approved, **(output_data or {})}
            if approved:
                ne_entity.succeed(merged_output)
            else:
                ne_entity.output_data = merged_output
            apply_node_execution_domain_to_model(ne_entity, node_execution)
            await self.repos.node_executions.update(node_execution)

            execution.context_variables = {**execution.context_variables, **merged_output}

            _nodes, edges = await self._load_graph(execution.workflow_version_id)
            outgoing = [e for e in edges if e.source_node_key == node_execution.node_key]
            next_key = outgoing[0].target_node_key if outgoing else None

            entity = execution_to_domain(execution)
            entity.resume()
            entity.current_node_key = next_key
            apply_execution_domain_to_model(entity, execution)
            await self.repos.executions.update(execution)

        return await self.run(execution_id)

    async def retry_node(self, execution_id: str, node_key: str) -> ExecutionModel:
        """Re-enters the run loop pointed at `node_key` — used after an
        operator fixes whatever caused a FAILED execution's node to fail
        (e.g. a bad REST_API config) rather than restarting the whole run."""
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            entity.retry_from_node(node_key)
            apply_execution_domain_to_model(entity, execution)
            await self.repos.executions.update(execution)
        return await self.run(execution_id)
