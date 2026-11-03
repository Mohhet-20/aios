"""Release approval workflow: gates a release's advance to production
behind at least one recorded `approved` decision. Decisions are
one-shot — deciding an already-decided approval raises `ConflictError`
rather than silently overwriting it, mirroring
`docs_platform.collaboration.ReviewService`'s `ReviewAlreadyDecidedError`
precedent (a fresh approval request should be filed instead of
mutating history)."""
from __future__ import annotations


from release_platform.core.exceptions import ConflictError, NotFoundError, ReleaseApprovalRequiredError, ValidationError
from release_platform.models.security import ReleaseApprovalModel
from release_platform.repositories.registry import RepositoryRegistry
from release_platform.clock import utc_now

_VALID_DECISIONS = {"approved", "rejected"}


class ReleaseApprovalService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_or_404(self, tenant_id: str, approval_id: str) -> ReleaseApprovalModel:
        approval = await self.repos.release_approvals.get(approval_id)
        if approval is None or approval.tenant_id != tenant_id:
            raise NotFoundError(f"Release approval '{approval_id}' not found for tenant '{tenant_id}'")
        return approval

    async def request_approval(self, tenant_id: str, *, release_id: str, approver_id: str) -> ReleaseApprovalModel:
        approval = ReleaseApprovalModel(tenant_id=tenant_id, release_id=release_id, approver_id=approver_id, decision="pending")
        return await self.repos.release_approvals.add(approval)

    async def decide(self, tenant_id: str, approval_id: str, *, decision: str, notes: str = "") -> ReleaseApprovalModel:
        if decision not in _VALID_DECISIONS:
            raise ValidationError(f"Unsupported approval decision '{decision}'")
        approval = await self.get_or_404(tenant_id, approval_id)
        if approval.decision != "pending":
            raise ConflictError(f"Release approval '{approval_id}' was already decided ('{approval.decision}')")
        approval.decision = decision
        approval.notes = notes
        approval.decided_at = utc_now()
        return approval

    async def list_for_release(self, tenant_id: str, release_id: str) -> list[ReleaseApprovalModel]:
        return await self.repos.release_approvals.list_for_release(tenant_id, release_id)

    async def assert_release_approved(self, tenant_id: str, release_id: str) -> None:
        approvals = await self.list_for_release(tenant_id, release_id)
        if not any(a.decision == "approved" for a in approvals):
            raise ReleaseApprovalRequiredError(f"Release '{release_id}' has no approved release-approval on record")
