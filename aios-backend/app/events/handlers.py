"""Default subscribers wiring domain events to cross-cutting concerns
(audit logging, notifications) so services that emit events don't need to
know or care who's listening — `PromptService.promote_version()` publishes
`PromptPromoted` and has zero knowledge that an audit log row gets written
as a result.

Handlers open their own DB session (`session_scope`) rather than reusing the
publisher's session, since they run as detached background tasks that may
execute after the original request's transaction has already committed.
"""

from __future__ import annotations

from app.database.session import session_scope
from app.domain.events.events import (
    AuditableActionPerformed,
    EvaluationCompleted,
    NotificationCreated,
    PromptPromoted,
    WorkflowExecutionCompleted,
)
from app.events.bus import EventBus
from app.logging.setup import get_logger
from app.models.audit import AuditLogModel
from app.models.notification import NotificationModel

logger = get_logger(__name__)


async def _handle_auditable_action(event: AuditableActionPerformed) -> None:
    async with session_scope() as session:
        session.add(
            AuditLogModel(
                organization_id=event.organization_id or "unknown",
                actor=event.actor_id or "system",
                action=event.action,
                resource=event.resource,
                status=event.status,
            )
        )


async def _handle_prompt_promoted(event: PromptPromoted) -> None:
    async with session_scope() as session:
        session.add(
            AuditLogModel(
                organization_id=event.organization_id or "unknown",
                actor=event.actor_id or "system",
                action="prompt.promote",
                resource=f"prompt:{event.prompt_id}:v{event.version}",
                status="success",
            )
        )
    logger.info(
        "prompt_promoted", prompt_id=event.prompt_id, version=event.version, to_status=event.to_status
    )


async def _handle_workflow_execution_completed(event: WorkflowExecutionCompleted) -> None:
    async with session_scope() as session:
        session.add(
            NotificationModel(
                recipient_user_id=event.actor_id or "system",
                title="Workflow execution finished",
                description=f"Execution {event.execution_id} {'succeeded' if event.success else 'failed'}.",
                notification_type="success" if event.success else "error",
            )
        )


async def _handle_evaluation_completed(event: EvaluationCompleted) -> None:
    async with session_scope() as session:
        session.add(
            NotificationModel(
                recipient_user_id=event.actor_id or "system",
                title="Evaluation completed",
                description=(
                    f"Run {event.evaluation_run_id} scored {event.score}% "
                    f"({event.passed} passed / {event.failed} failed)."
                ),
                notification_type="success" if event.score >= 90 else "warning",
            )
        )


async def _handle_notification_created(event: NotificationCreated) -> None:
    logger.info(
        "notification_dispatched", notification_id=event.notification_id, recipient=event.recipient_user_id
    )


def register_default_handlers(bus: EventBus) -> None:
    bus.subscribe(AuditableActionPerformed, _handle_auditable_action)
    bus.subscribe(PromptPromoted, _handle_prompt_promoted)
    bus.subscribe(WorkflowExecutionCompleted, _handle_workflow_execution_completed)
    bus.subscribe(EvaluationCompleted, _handle_evaluation_completed)
    bus.subscribe(NotificationCreated, _handle_notification_created)
