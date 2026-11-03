"""Human-in-the-loop node handlers. APPROVAL creates a real
`ApprovalRequestModel` row and hands control back to the engine, which
transitions the execution to WAITING_APPROVAL and returns — deciding the
approval (`approval/approval_service.py`) is what eventually calls
`ExecutionEngine.resume_after_approval` to unblock the run. `escalate_
after_seconds`/`expires_after_seconds` on the node config become real
`escalate_after`/`expires_at` timestamps `ApprovalService`'s escalation
sweep and expiry sweep act on. NOTIFICATION writes a structured
execution-log entry and publishes a real event through the Event System
via the `event_publisher` hook the engine injects."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from workflow_platform.core.exceptions import NodeExecutionError
from workflow_platform.database.base import utcnow
from workflow_platform.domain.enums import EventType
from workflow_platform.models.approval import ApprovalRequestModel
from workflow_platform.models.observability import ExecutionLogModel
from workflow_platform.workflow_engine.context import NodeContext
from workflow_platform.workflow_engine.handlers.base import NodeHandler


class ApprovalHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        repos = ctx.extra.get("repos")
        if repos is None:
            raise NodeExecutionError("APPROVAL node requires the engine's repository registry")
        chain = ctx.config.get("approval_chain") or [[ctx.execution.triggered_by or "unassigned"]]
        sensitivity_level = ctx.config.get("sensitivity_level", "normal")

        approval_policy = ctx.extra.get("approval_policy")
        if approval_policy is not None:
            from workflow_platform.core.exceptions import ValidationError
            try:
                approval_policy.validate_chain(chain, sensitivity_level)
            except ValidationError as exc:
                raise NodeExecutionError(str(exc)) from exc

        now = utcnow()
        escalate_after_seconds = ctx.config.get("escalate_after_seconds")
        expires_after_seconds = ctx.config.get("expires_after_seconds")

        request = await repos.approval_requests.add(ApprovalRequestModel(
            execution_id=ctx.execution.id, node_execution_id=ctx.node_execution.id, workspace_id=ctx.execution.workspace_id,
            requested_by=ctx.execution.triggered_by or "system", approval_chain=chain,
            reason=ctx.config.get("reason"), sensitivity_level=sensitivity_level,
            escalate_after=now + timedelta(seconds=escalate_after_seconds) if escalate_after_seconds else None,
            expires_at=now + timedelta(seconds=expires_after_seconds) if expires_after_seconds else None,
        ))

        publisher = ctx.extra.get("event_publisher")
        if publisher is not None:
            await publisher(
                event_type=EventType.APPROVAL_REQUESTED.value, workspace_id=ctx.execution.workspace_id,
                source_type="approval", source_id=request.id,
                payload={"execution_id": ctx.execution.id, "reason": request.reason, "approval_chain": chain},
            )

        return {"approval_request_id": request.id, "approval_chain": chain}


class NotificationHandler(NodeHandler):
    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        repos = ctx.extra.get("repos")
        message = ctx.config.get("message", "").format(**ctx.variables) if isinstance(ctx.config.get("message"), str) else str(ctx.config.get("message"))
        if repos is not None:
            await repos.execution_logs.add(ExecutionLogModel(
                execution_id=ctx.execution.id, node_execution_id=ctx.node_execution.id, level="info",
                message=f"[notification] {message}", log_metadata={"channel": ctx.config.get("channel", "default")},
            ))
        await self._publish(ctx, message)
        return {"notified": True, "message": message}

    async def _publish(self, ctx: NodeContext, message: str) -> None:
        publisher = ctx.extra.get("event_publisher")
        if publisher is not None:
            await publisher(event_type="node_completed", workspace_id=ctx.execution.workspace_id, source_type="node",
                             source_id=ctx.node.id, payload={"message": message})
