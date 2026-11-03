"""ApprovalService: the decision side of Human-in-the-Loop — everything
`workflow_engine/handlers/human.py`'s `ApprovalHandler` doesn't do itself
when it pauses an execution at an APPROVAL node. Owns: authorizing and
recording a step decision, walking multi-step `approval_chain`s,
rejection handling, reassignment, comments, escalation, expiry, and the
audit trail — then calls `ExecutionEngine.resume_after_approval` to
actually unblock the paused run once a chain is fully resolved (approved
or rejected).

`approval_chain` is `[[approver_ids...], [approver_ids...], ...]` — step
`current_step` needs a decision from any *one* id in
`approval_chain[current_step]`. Approving a non-final step just advances
`current_step` (the request stays PENDING); approving the final step —
or rejecting at any step — is what actually resolves the request and
resumes execution."""
from __future__ import annotations

from workflow_platform.core.exceptions import AuthorizationError, InvalidTransitionError, ValidationError
from workflow_platform.database.base import utcnow
from workflow_platform.domain.entities import ApprovalRequest
from workflow_platform.domain.enums import ApprovalStatus, EventType
from workflow_platform.models.approval import ApprovalCommentModel, ApprovalRequestModel
from workflow_platform.models.governance import AuditLogEntryModel
from workflow_platform.repositories.registry import RepositoryRegistry


def _approval_to_domain(model: ApprovalRequestModel) -> ApprovalRequest:
    return ApprovalRequest(
        id=model.id, execution_id=model.execution_id, node_execution_id=model.node_execution_id,
        workspace_id=model.workspace_id, requested_by=model.requested_by, status=ApprovalStatus(model.status),
        approval_chain=list(model.approval_chain or []), current_step=model.current_step, reason=model.reason,
        sensitivity_level=model.sensitivity_level, decided_by=model.decided_by, decision_notes=model.decision_notes,
        escalated_at=model.escalated_at, decided_at=model.decided_at,
    )


def _apply_approval_domain_to_model(entity: ApprovalRequest, model: ApprovalRequestModel) -> None:
    model.status = entity.status.value
    model.current_step = entity.current_step
    model.decided_by = entity.decided_by
    model.decision_notes = entity.decision_notes
    model.escalated_at = entity.escalated_at
    model.decided_at = entity.decided_at


class ApprovalService:
    def __init__(self, repos: RepositoryRegistry, *, engine=None, event_bus=None):
        self.repos = repos
        self.engine = engine
        self.event_bus = event_bus

    async def _publish(self, event_type: str, request: ApprovalRequestModel, **payload) -> None:
        if self.event_bus is None:
            return
        await self.event_bus.publish(
            event_type=event_type, workspace_id=request.workspace_id, source_type="approval",
            source_id=request.id, payload={"execution_id": request.execution_id, **payload},
        )

    async def _audit(self, actor_id: str, action: str, request: ApprovalRequestModel, *, before: dict, after: dict) -> None:
        await self.repos.audit_log.add(AuditLogEntryModel(
            actor_id=actor_id, action=action, resource_type="approval_request", resource_id=request.id,
            before=before, after=after,
        ))

    def _require_decidable(self, request: ApprovalRequestModel) -> None:
        if request.status not in (ApprovalStatus.PENDING.value, ApprovalStatus.ESCALATED.value):
            raise InvalidTransitionError(
                f"approval request '{request.id}' is already {request.status} and cannot be decided again"
            )

    def _current_step_approvers(self, request: ApprovalRequestModel) -> list[str]:
        chain = request.approval_chain or []
        if request.current_step >= len(chain):
            raise ValidationError(f"approval request '{request.id}' has no remaining chain step")
        return list(chain[request.current_step])

    async def approve_step(self, approval_id: str, *, decided_by: str, notes: str | None = None) -> ApprovalRequestModel:
        request = await self.repos.approval_requests.get_or_404(approval_id)
        self._require_decidable(request)
        if decided_by not in self._current_step_approvers(request):
            raise AuthorizationError(
                f"'{decided_by}' is not an authorized approver for step {request.current_step} of request '{approval_id}'"
            )
        before = {"status": request.status, "current_step": request.current_step}

        entity = _approval_to_domain(request)
        has_more_steps = entity.advance_step()

        if has_more_steps:
            _apply_approval_domain_to_model(entity, request)
            request = await self.repos.approval_requests.update(request)
            await self._audit(decided_by, "approval_step_approved", request, before=before, after={"status": request.status, "current_step": request.current_step})
            await self._publish(EventType.APPROVAL_DECIDED.value, request, decision="step_approved", decided_by=decided_by, current_step=request.current_step)
            return request

        entity.approve(decided_by=decided_by, notes=notes)
        _apply_approval_domain_to_model(entity, request)
        request = await self.repos.approval_requests.update(request)
        await self._audit(decided_by, "approval_approved", request, before=before, after={"status": request.status})
        await self._publish(EventType.APPROVAL_DECIDED.value, request, decision="approved", decided_by=decided_by)

        if self.engine is not None:
            await self.engine.resume_after_approval(request.execution_id, approved=True)
        return request

    async def reject(self, approval_id: str, *, decided_by: str, notes: str | None = None) -> ApprovalRequestModel:
        request = await self.repos.approval_requests.get_or_404(approval_id)
        self._require_decidable(request)
        if decided_by not in self._current_step_approvers(request):
            raise AuthorizationError(
                f"'{decided_by}' is not an authorized approver for step {request.current_step} of request '{approval_id}'"
            )
        before = {"status": request.status, "current_step": request.current_step}

        entity = _approval_to_domain(request)
        entity.reject(decided_by=decided_by, notes=notes)
        _apply_approval_domain_to_model(entity, request)
        request = await self.repos.approval_requests.update(request)
        await self._audit(decided_by, "approval_rejected", request, before=before, after={"status": request.status})
        await self._publish(EventType.APPROVAL_DECIDED.value, request, decision="rejected", decided_by=decided_by)

        if self.engine is not None:
            await self.engine.resume_after_approval(request.execution_id, approved=False)
        return request

    async def reassign_step(self, approval_id: str, *, new_approvers: list[str], reassigned_by: str) -> ApprovalRequestModel:
        if not new_approvers:
            raise ValidationError("reassignment requires at least one approver")
        request = await self.repos.approval_requests.get_or_404(approval_id)
        chain = list(request.approval_chain or [])
        if request.current_step >= len(chain):
            raise ValidationError(f"approval request '{approval_id}' has no remaining chain step to reassign")
        before = {"approval_chain": chain}
        chain[request.current_step] = list(new_approvers)
        request.approval_chain = chain
        request = await self.repos.approval_requests.update(request)
        await self._audit(reassigned_by, "approval_step_reassigned", request, before=before, after={"approval_chain": chain})
        return request

    # -- escalation / expiry -----------------------------------------------------

    async def escalate(self, approval_id: str) -> ApprovalRequestModel:
        request = await self.repos.approval_requests.get_or_404(approval_id)
        entity = _approval_to_domain(request)
        entity.escalate()
        _apply_approval_domain_to_model(entity, request)
        request = await self.repos.approval_requests.update(request)
        await self._publish(EventType.APPROVAL_REQUESTED.value, request, decision="escalated")
        return request

    async def run_escalation_sweep(self, *, as_of=None) -> list[ApprovalRequestModel]:
        candidates = await self.repos.approval_requests.list_escalation_candidates(as_of=as_of or utcnow())
        escalated = []
        for request in candidates:
            escalated.append(await self.escalate(request.id))
        return escalated

    async def expire(self, approval_id: str) -> ApprovalRequestModel:
        request = await self.repos.approval_requests.get_or_404(approval_id)
        entity = _approval_to_domain(request)
        entity.expire()
        _apply_approval_domain_to_model(entity, request)
        request = await self.repos.approval_requests.update(request)
        await self._publish(EventType.APPROVAL_DECIDED.value, request, decision="expired")
        if self.engine is not None:
            await self.engine.resume_after_approval(request.execution_id, approved=False, output_data={"expired": True})
        return request

    # -- comments -----------------------------------------------------------------

    async def add_comment(self, approval_id: str, *, author_id: str, comment: str) -> ApprovalCommentModel:
        await self.repos.approval_requests.get_or_404(approval_id)  # 404s if missing
        return await self.repos.approval_comments.add(ApprovalCommentModel(
            approval_request_id=approval_id, author_id=author_id, comment=comment,
        ))

    async def list_comments(self, approval_id: str) -> list[ApprovalCommentModel]:
        return await self.repos.approval_comments.list_for_approval(approval_id)

    # -- queries --------------------------------------------------------------------

    async def list_pending_for_workspace(self, workspace_id: str) -> list[ApprovalRequestModel]:
        return await self.repos.approval_requests.list_pending_for_workspace(workspace_id)

    async def list_for_execution(self, execution_id: str) -> list[ApprovalRequestModel]:
        return await self.repos.approval_requests.list_for_execution(execution_id)
