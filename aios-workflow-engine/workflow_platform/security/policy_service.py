"""Execution Policies and Approval Policies — the two policy surfaces
Phase 8 calls out by name, distinct from RBAC (who has what role) and
from Governance's audit trail (what happened). An Execution Policy
answers "is this principal allowed to start/control this execution
right now"; an Approval Policy answers "does this approval request meet
the bar its sensitivity level demands" (e.g. a CRITICAL-sensitivity
approval needs more than one sign-off, regardless of what chain a
workflow author happened to configure on the node)."""
from __future__ import annotations

from workflow_platform.core.exceptions import ValidationError
from workflow_platform.domain.enums import Permission
from workflow_platform.models.execution import ExecutionModel
from workflow_platform.models.workflow import WorkflowModel
from workflow_platform.security.rbac_service import RBACService


class ExecutionPolicyService:
    def __init__(self, rbac: RBACService):
        self.rbac = rbac

    async def authorize_start_execution(self, principal_id: str, workflow: WorkflowModel) -> None:
        await self.rbac.require_permission(
            principal_id, Permission.WORKFLOW_EXECUTE, workspace_id=workflow.workspace_id, workflow_id=workflow.id,
        )

    async def authorize_control_execution(self, principal_id: str, execution: ExecutionModel) -> None:
        """Pause/resume/cancel/retry — anything that changes a run already
        in flight."""
        await self.rbac.require_permission(principal_id, Permission.EXECUTION_CONTROL, workspace_id=execution.workspace_id)


class ApprovalPolicyService:
    """Minimum required approval-chain length per `sensitivity_level` —
    a workflow author can always configure a *longer* chain, but can't
    configure a shorter one than the sensitivity level demands."""

    _MIN_CHAIN_LENGTH = {"low": 1, "normal": 1, "high": 2, "critical": 3}

    def required_chain_length(self, sensitivity_level: str) -> int:
        return self._MIN_CHAIN_LENGTH.get(sensitivity_level, 1)

    def validate_chain(self, approval_chain: list, sensitivity_level: str) -> None:
        required = self.required_chain_length(sensitivity_level)
        if len(approval_chain) < required:
            raise ValidationError(
                f"approval sensitivity '{sensitivity_level}' requires a chain of at least {required} "
                f"step(s), got {len(approval_chain)}"
            )
