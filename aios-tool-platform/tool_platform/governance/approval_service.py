"""ApprovalService: the human-in-the-loop checkpoint for HIGH/CRITICAL
sensitivity tool calls (see `ToolSensitivity`'s docstring). A gate is
requested, approved or rejected, and — critically — *consumed* exactly
once by the Execution Engine at the moment it actually spends the
approval to start a call. `consume()` is the piece that keeps an
APPROVED gate from being replayed across multiple executions: once
consumed_at is set, the gate can never be consumed again, so a caller
must request a fresh gate per sensitive call rather than approving once
and executing indefinitely."""
from __future__ import annotations


from tool_platform.core.exceptions import ValidationError
from tool_platform.domain.enums import ApprovalStatus
from tool_platform.models.governance import ApprovalGateModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.clock import utc_now


class ApprovalService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def request_approval(
        self, resource_type: str, resource_id: str, *, requested_by: str, reason: str | None = None,
        sensitivity_level: str = "high",
    ) -> ApprovalGateModel:
        return await self.repos.approval_gates.add(ApprovalGateModel(
            resource_type=resource_type, resource_id=resource_id, requested_by=requested_by,
            reason=reason, sensitivity_level=sensitivity_level,
        ))

    async def approve(self, gate_id: str, *, approver_id: str, notes: str | None = None) -> ApprovalGateModel:
        gate = await self._require_pending(gate_id)
        gate.status = ApprovalStatus.APPROVED.value
        gate.approver_id = approver_id
        gate.decision_notes = notes
        gate.resolved_at = utc_now()
        return await self.repos.approval_gates.update(gate)

    async def reject(self, gate_id: str, *, approver_id: str, notes: str | None = None) -> ApprovalGateModel:
        gate = await self._require_pending(gate_id)
        gate.status = ApprovalStatus.REJECTED.value
        gate.approver_id = approver_id
        gate.decision_notes = notes
        gate.resolved_at = utc_now()
        return await self.repos.approval_gates.update(gate)

    async def _require_pending(self, gate_id: str) -> ApprovalGateModel:
        gate = await self.repos.approval_gates.get_or_404(gate_id)
        if gate.status != ApprovalStatus.PENDING.value:
            raise ValidationError(f"approval gate '{gate_id}' is {gate.status}, not pending — cannot decide it again")
        return gate

    async def consume(self, gate_id: str, *, resource_type: str, resource_id: str) -> ApprovalGateModel:
        """Called by the Execution Engine immediately before it dispatches
        a sensitive tool call. Raises if the gate doesn't match the exact
        resource it's being spent for, isn't APPROVED, or has already been
        consumed once — each a distinct, named failure rather than one
        generic rejection."""
        gate = await self.repos.approval_gates.get_or_404(gate_id)
        if gate.resource_type != resource_type or gate.resource_id != resource_id:
            raise ValidationError(
                f"approval gate '{gate_id}' was requested for {gate.resource_type} '{gate.resource_id}', "
                f"not {resource_type} '{resource_id}'"
            )
        if gate.status != ApprovalStatus.APPROVED.value:
            raise ValidationError(f"approval gate '{gate_id}' is {gate.status}, not approved")
        if gate.consumed_at is not None:
            raise ValidationError(f"approval gate '{gate_id}' was already consumed at {gate.consumed_at.isoformat()}")

        gate.consumed_at = utc_now()
        return await self.repos.approval_gates.update(gate)

    async def list_pending(self, *, resource_type: str | None = None) -> list[ApprovalGateModel]:
        return await self.repos.approval_gates.list_pending(resource_type=resource_type)

    async def list_for_resource(self, resource_type: str, resource_id: str) -> list[ApprovalGateModel]:
        return await self.repos.approval_gates.list_for_resource(resource_type, resource_id)
