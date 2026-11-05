"""ToolExecutionEngine — the execution backbone for a single tool call,
scoped much narrower than the Workflow Engine's graph-walking engine
(there's no node graph here, just: validate input -> dispatch to one
connector -> validate output -> retry/timeout/checkpoint/rollback), but
built on the exact same concurrency model: one `asyncio.Lock`
(`_session_lock`) serializes every repository/session touch, since a
SQLAlchemy AsyncSession isn't safe for concurrent coroutine access, while
the actual connector `execute()` call — genuine I/O — runs OUTSIDE that
lock. That's what makes BATCH/PARALLEL execution (`run_batch`) real
concurrency rather than serialized work wearing a "parallel" label: N
concurrent `start_execution` calls each acquire and release the lock
only for their own brief DB writes, spending the rest of their time
awaiting the connector concurrently.

Retry policy mirrors the Workflow Engine's node retry loop exactly: the
engine decides whether another attempt is allowed (`attempt_number <=
max_retries`) BEFORE calling the domain entity's `retry()`, rather than
leaning on `retry()`'s own guard for control flow — that guard is a
safety net, not the decision point.

Cancellation is honest about its own limit: `cancel_execution` can only
ever flip a PENDING/QUEUED/orphaned-RUNNING row to CANCELLED in the
database. It cannot reach into another coroutine's in-flight
`asyncio.wait_for(handler.execute(...))` call and interrupt it — doing
that for real would require the engine to track and cancel the
underlying `asyncio.Task`, which this implementation doesn't do. A
production deployment wanting true mid-flight cancellation would need
that task-tracking layer; this cancels "the next chance the engine
looks," not "right now.\""""
from __future__ import annotations

import asyncio

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as jsonschema_validate

from tool_platform.core.exceptions import ApprovalRequiredError, ToolExecutionError, ValidationError
from tool_platform.domain.enums import ExecutionStatus
from tool_platform.models.checkpoint import ExecutionCheckpointModel
from tool_platform.models.execution import ToolExecutionModel
from tool_platform.models.observability import ExecutionLogModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.mappers import apply_execution_domain_to_model, execution_to_domain
from tool_platform.tool_execution.registry import ConnectorRegistry


class ToolExecutionEngine:
    def __init__(
        self, repos: RepositoryRegistry, connectors: ConnectorRegistry, *, vault=None, ai_core=None,
        network_policy=None, sleep_fn=asyncio.sleep, max_batch_concurrency: int = 10,
        policy_engine=None, approval_service=None, audit_service=None,
    ):
        self.repos = repos
        self.connectors = connectors
        self.vault = vault
        self.ai_core = ai_core
        self.network_policy = network_policy
        self._sleep = sleep_fn
        self._max_batch_concurrency = max_batch_concurrency
        self._session_lock = asyncio.Lock()
        # Governance is entirely optional injection, same pattern the Agent
        # Platform's orchestrator uses for its PolicyEngine/ApprovalService:
        # a caller that doesn't wire these gets the platform's pre-original
        # behavior exactly, unchanged.
        self.policy_engine = policy_engine
        self.approval_service = approval_service
        self.audit_service = audit_service

    # -- starting a call ---------------------------------------------------------

    async def start_execution(
        self, tool_id: str, *, input_data: dict | None = None, execution_mode: str = "sync",
        triggered_by: str | None = None, trigger_type: str = "manual", priority: str = "normal",
        parent_execution_id: str | None = None, credential_id: str | None = None,
        approval_gate_id: str | None = None,
    ) -> ToolExecutionModel:
        # Every repo/session touch below — including PolicyEngine's and
        # ApprovalService's, both of which read/write through the same
        # shared self.repos — stays inside this single `_session_lock`
        # acquisition. Splitting governance checks into their own
        # unlocked section was tried and reverted: a SQLAlchemy
        # AsyncSession has exactly one flush in flight at a time, so two
        # `run_batch(execution_mode="parallel")` branches concurrently
        # calling e.g. `check_tool_concurrency_quota` outside the lock
        # produced "Session is already flushing" under real concurrency
        # — a genuine bug caught by the batch-execution API test, not a
        # hypothetical one. The connector call itself is still the only
        # thing that ever runs unlocked (see `run()` below).
        async with self._session_lock:
            tool = await self.repos.tools.get_or_404(tool_id)
            if not tool.current_version_id:
                raise ValidationError(f"tool '{tool_id}' has no published version to execute")
            version = await self.repos.tool_versions.get_or_404(tool.current_version_id)

            if self.policy_engine is not None:
                if triggered_by is not None:
                    await self.policy_engine.check_rate_limit(triggered_by)
                await self.policy_engine.check_tool_concurrency_quota(tool)
                await self.policy_engine.check_workspace_concurrency_quota(tool.workspace_id)

                if self.policy_engine.requires_approval(version):
                    if self.approval_service is None or not approval_gate_id:
                        raise ApprovalRequiredError(
                            f"tool version '{version.id}' has sensitivity_level='{version.sensitivity_level}' and "
                            "requires a resolved, unconsumed approval gate — call ApprovalService.request_approval() "
                            "then pass its id as approval_gate_id"
                        )
                    await self.approval_service.consume(approval_gate_id, resource_type="tool", resource_id=tool_id)

            execution = await self.repos.executions.add(ToolExecutionModel(
                tool_id=tool_id, tool_version_id=version.id, workspace_id=tool.workspace_id,
                execution_mode=execution_mode, priority=priority, input_data=input_data or {},
                credential_id=credential_id, triggered_by=triggered_by, trigger_type=trigger_type,
                parent_execution_id=parent_execution_id, max_retries=version.default_max_retries,
                timeout_seconds=version.default_timeout_seconds, retry_backoff_seconds=version.default_retry_backoff_seconds,
            ))

            if self.audit_service is not None:
                await self.audit_service.record(
                    triggered_by or "system", "tool.execute", "tool", tool_id, after={"execution_id": execution.id},
                )

        return await self.run(execution.id)

    # -- the run loop --------------------------------------------------------------

    async def run(self, execution_id: str) -> ToolExecutionModel:
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            tool = await self.repos.tools.get_or_404(execution.tool_id)
            version = await self.repos.tool_versions.get_or_404(execution.tool_version_id)

            entity = execution_to_domain(execution)
            if entity.status == ExecutionStatus.RETRYING:
                entity.resume_after_retry()
            elif entity.status in (ExecutionStatus.PENDING, ExecutionStatus.QUEUED):
                entity.start()
            else:
                raise ValidationError(f"execution '{execution_id}' cannot run from status {entity.status.value}")
            apply_execution_domain_to_model(entity, execution)
            execution = await self.repos.executions.update(execution)

        input_error = self._validate_schema(version.input_schema, execution.input_data, label="input")
        if input_error:
            return await self._finish_failure(execution_id, input_error, timeout=False)

        credential_secret = None
        if execution.credential_id and self.vault is not None:
            async with self._session_lock:
                credential_secret = await self.vault.get_secret(execution.credential_id)

        handler = self.connectors.get(version.connector_key)
        ctx = ToolCallContext(
            tool=tool, tool_version=version, execution=execution, input_data=dict(execution.input_data),
            config=dict(version.configuration), credential_secret=credential_secret, ai_core=self.ai_core,
            network_policy=self.network_policy, extra={"repos": self.repos},
        )

        try:
            output = await asyncio.wait_for(handler.execute(ctx), timeout=execution.timeout_seconds)
        except asyncio.TimeoutError:
            return await self._finish_failure(
                execution_id, f"tool call exceeded its {execution.timeout_seconds}s timeout", timeout=True,
            )
        except ToolExecutionError as exc:
            return await self._finish_failure(execution_id, str(exc), timeout=False)
        except Exception as exc:  # noqa: BLE001 — any connector bug still needs to become a recorded failure
            return await self._finish_failure(execution_id, f"{type(exc).__name__}: {exc}", timeout=False)

        output_error = self._validate_schema(version.output_schema, output, label="output")
        if output_error:
            return await self._finish_failure(execution_id, output_error, timeout=False)

        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            entity.succeed(output)
            apply_execution_domain_to_model(entity, execution)
            execution.sandbox_usage = self._extract_sandbox_usage(output)
            execution = await self.repos.executions.update(execution)
            await self._checkpoint(execution)
            await self._log(execution, "info", f"execution succeeded in {entity.duration_ms or 0:.1f}ms")
        return execution

    _SANDBOX_USAGE_FIELDS = ("cpu_seconds", "peak_memory_mb", "disk_mb", "network_bytes")

    def _extract_sandbox_usage(self, output: dict) -> dict:
        """Connectors that genuinely measure resource usage (currently
        `PythonExecutionHandler`/`ShellCommandHandler` via the subprocess
        sandbox's real rlimit + getrusage measurement) surface it as
        top-level fields on their output dict. This lifts exactly those
        fields — never more, never fabricated — into the execution's
        `sandbox_usage` column, which is the only place Observability
        reads resource-usage data from. A connector that never measured
        anything (echo, http_client, database_query, ...) contributes an
        empty dict, which Observability already treats as "no sample"
        rather than a fabricated zero."""
        if not isinstance(output, dict):
            return {}
        return {field: output[field] for field in self._SANDBOX_USAGE_FIELDS if field in output and output[field] is not None}

    async def _finish_failure(self, execution_id: str, error_message: str, *, timeout: bool) -> ToolExecutionModel:
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            if timeout:
                entity.timeout(error_message)
            else:
                entity.fail(error_message)
            apply_execution_domain_to_model(entity, execution)
            execution = await self.repos.executions.update(execution)
            await self._checkpoint(execution)

            should_retry = entity.attempt_number <= entity.max_retries
            if should_retry:
                entity.retry()
                apply_execution_domain_to_model(entity, execution)
                execution = await self.repos.executions.update(execution)
                await self._log(execution, "warning", f"attempt {entity.attempt_number - 1} failed, retrying: {error_message}")
            else:
                await self._log(execution, "error", f"execution failed permanently after {entity.attempt_number} attempt(s): {error_message}")

        if should_retry:
            backoff = execution.retry_backoff_seconds * (2 ** (entity.attempt_number - 2))
            await self._sleep(backoff)
            return await self.run(execution_id)
        return execution

    def _validate_schema(self, schema: dict, data: dict, *, label: str) -> str | None:
        if not schema:
            return None
        try:
            jsonschema_validate(instance=data, schema=schema)
            return None
        except JsonSchemaValidationError as exc:
            return f"{label} failed schema validation: {exc.message}"

    async def _checkpoint(self, execution: ToolExecutionModel) -> None:
        """Caller must already hold `self._session_lock`."""
        existing = await self.repos.checkpoints.list_for_execution(execution.id)
        await self.repos.checkpoints.add(ExecutionCheckpointModel(
            execution_id=execution.id, sequence_number=len(existing) + 1,
            state_snapshot={"status": execution.status, "output_data": execution.output_data, "attempt_number": execution.attempt_number},
        ))

    async def _log(self, execution: ToolExecutionModel, level: str, message: str) -> None:
        """Caller must already hold `self._session_lock`."""
        await self.repos.execution_logs.add(ExecutionLogModel(execution_id=execution.id, level=level, message=message))

    # -- control -------------------------------------------------------------------

    async def cancel_execution(self, execution_id: str) -> ToolExecutionModel:
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            entity.cancel()
            apply_execution_domain_to_model(entity, execution)
            return await self.repos.executions.update(execution)

    async def sweep_stalled_executions(self, *, stalled_after_seconds: int, as_of=None) -> list[ToolExecutionModel]:
        """Failure recovery for the one failure mode `cancel_execution`'s
        own docstring already anticipates: a RUNNING row whose owning
        process crashed mid-call rather than one that's genuinely still
        working — no heartbeat ever updates `started_at` again, so it
        would sit RUNNING forever without this sweep. Reuses the exact
        same RUNNING -> CANCELLED transition `cancel_execution` uses for
        an operator-initiated cancel; a sweep-recovered row is
        indistinguishable in the database from one a human cancelled,
        which is the honest description of what happened (this platform
        has no in-flight `asyncio.Task` handle to actually interrupt, so
        "cancelled" means "given up on," not "stopped mid-flight" — see
        the class docstring's cancellation-honesty note)."""
        import datetime as _dt

        as_of = as_of or _dt.datetime.now(_dt.timezone.utc)
        cutoff = as_of - _dt.timedelta(seconds=stalled_after_seconds)

        async with self._session_lock:
            stalled = await self.repos.executions.list_stalled_running(older_than=cutoff)

        recovered: list[ToolExecutionModel] = []
        for execution in stalled:
            async with self._session_lock:
                entity = execution_to_domain(execution)
                entity.cancel()
                apply_execution_domain_to_model(entity, execution)
                execution = await self.repos.executions.update(execution)
                await self._log(
                    execution, "warning",
                    f"recovered: execution appeared stalled (no progress since before {cutoff.isoformat()}) — cancelled",
                )
            recovered.append(execution)
        return recovered

    async def retry_execution(self, execution_id: str) -> ToolExecutionModel:
        """Operator-triggered retry after automatic retries were already
        exhausted — resets the attempt counter rather than relying on the
        domain entity's own remaining-attempts guard, since this is a
        deliberate override of that budget, not another automatic attempt."""
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            entity = execution_to_domain(execution)
            entity.attempt_number = 0
            entity.retry()
            apply_execution_domain_to_model(entity, execution)
            await self.repos.executions.update(execution)
        return await self.run(execution_id)

    async def rollback_execution(self, execution_id: str) -> ToolExecutionModel:
        async with self._session_lock:
            execution = await self.repos.executions.get_or_404(execution_id)
            tool = await self.repos.tools.get_or_404(execution.tool_id)
            version = await self.repos.tool_versions.get_or_404(execution.tool_version_id)
            entity = execution_to_domain(execution)
            entity.rollback()
            apply_execution_domain_to_model(entity, execution)
            execution = await self.repos.executions.update(execution)

        handler = self.connectors.get(version.connector_key)
        ctx = ToolCallContext(
            tool=tool, tool_version=version, execution=execution, input_data=dict(execution.input_data),
            config=dict(version.configuration), ai_core=self.ai_core, network_policy=self.network_policy,
            extra={"repos": self.repos},
        )
        try:
            await handler.compensate(ctx)
        except Exception as exc:  # noqa: BLE001 — rollback is best-effort; the execution stays ROLLED_BACK regardless
            async with self._session_lock:
                await self._log(execution, "error", f"compensation failed: {type(exc).__name__}: {exc}")
        return execution

    # -- batch / parallel -----------------------------------------------------------

    async def run_batch(
        self, tool_id: str, input_batches: list[dict], *, execution_mode: str = "parallel",
        triggered_by: str | None = None, credential_id: str | None = None, max_concurrency: int | None = None,
    ) -> tuple[ToolExecutionModel, list[ToolExecutionModel]]:
        """Returns (parent_execution, child_executions). The parent row is
        bookkeeping only — it never calls a connector itself, just rolls
        up whether every child call succeeded."""
        async with self._session_lock:
            tool = await self.repos.tools.get_or_404(tool_id)
            if not tool.current_version_id:
                raise ValidationError(f"tool '{tool_id}' has no published version to execute")
            parent = await self.repos.executions.add(ToolExecutionModel(
                tool_id=tool_id, tool_version_id=tool.current_version_id, workspace_id=tool.workspace_id,
                execution_mode="batch", input_data={"batch_size": len(input_batches)}, max_retries=0,
                triggered_by=triggered_by,
            ))
            parent_entity = execution_to_domain(parent)
            parent_entity.start()
            apply_execution_domain_to_model(parent_entity, parent)
            parent = await self.repos.executions.update(parent)

        if execution_mode == "parallel":
            semaphore = asyncio.Semaphore(max_concurrency or self._max_batch_concurrency)

            async def _run_one(item: dict) -> ToolExecutionModel:
                async with semaphore:
                    return await self.start_execution(
                        tool_id, input_data=item, execution_mode="sync", triggered_by=triggered_by,
                        parent_execution_id=parent.id, credential_id=credential_id,
                    )

            children = await asyncio.gather(*(_run_one(item) for item in input_batches))
        else:
            children = []
            for item in input_batches:
                children.append(await self.start_execution(
                    tool_id, input_data=item, execution_mode="sync", triggered_by=triggered_by,
                    parent_execution_id=parent.id, credential_id=credential_id,
                ))

        async with self._session_lock:
            parent = await self.repos.executions.get_or_404(parent.id)
            parent_entity = execution_to_domain(parent)
            all_succeeded = all(c.status == ExecutionStatus.SUCCEEDED.value for c in children)
            if all_succeeded:
                parent_entity.succeed({"child_count": len(children)})
            else:
                failed_count = sum(1 for c in children if c.status != ExecutionStatus.SUCCEEDED.value)
                parent_entity.fail(f"{failed_count}/{len(children)} batch item(s) failed")
            apply_execution_domain_to_model(parent_entity, parent)
            parent = await self.repos.executions.update(parent)

        return parent, list(children)
