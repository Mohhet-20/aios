"""Approval workflows for governed assets: request approval (pulling
the required-approvals count from a tenant's `ApprovalPolicyModel` for
the asset type, falling back to `settings.default_required_approvals`
when no policy is configured), record each approver's decision, and —
once the request crosses its required-approvals threshold — promote
the underlying governance asset straight to whatever lifecycle stage
the request targeted. That promotion intentionally bypasses
`GovernanceAssetService.advance_stage`'s forward-only ordering check:
a human approval chain is itself the authority for the jump, the same
way `GuardrailService`'s custom-rule override bypasses the default
risk threshold.

`record_decision` reads the current approval count, decides whether
this decision crosses the threshold, then persists the decision row
and (possibly) promotes the asset — a check-then-act sequence spanning
multiple statements. Two approvers deciding concurrently on the same
request could otherwise both read the same "count so far" and neither
see the other's vote, so the whole sequence (including the commit) is
serialized per request_id with an in-process `asyncio.Lock`, the same
commit-spanning-lock pattern used throughout the AIOS build."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from security_platform.config.settings import Settings, get_settings
from security_platform.core.exceptions import ValidationError
from security_platform.domain.entities import ApprovalRequest as ApprovalEntity
from security_platform.domain.enums import ApprovalStatus
from security_platform.models.governance import ApprovalDecisionModel, ApprovalRequestModel
from security_platform.repositories.registry import RepositoryRegistry

_VALID_DECISIONS = {"approve", "reject"}


class ApprovalWorkflowService:
    _decision_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def request_approval(
        self, tenant_id: str, asset_id: str, *, asset_type: str, requested_by: str | None = None, target_lifecycle_stage: str | None = None
    ) -> ApprovalRequestModel:
        policy = await self.repos.approval_policies.get_for_asset_type(tenant_id, asset_type)
        required = policy.required_approvals if policy is not None else self.settings.default_required_approvals
        request = ApprovalRequestModel(
            tenant_id=tenant_id, asset_id=asset_id, requested_by=requested_by, status=ApprovalStatus.PENDING.value,
            required_approvals=required, target_lifecycle_stage=target_lifecycle_stage,
        )
        return await self.repos.approval_requests.add(request)

    async def record_decision(
        self, tenant_id: str, request_id: str, approver_id: str, decision: str, *, comment: str | None = None
    ) -> ApprovalRequestModel:
        if decision not in _VALID_DECISIONS:
            raise ValidationError(f"Unknown approval decision '{decision}'")
        async with self._decision_locks[request_id]:
            request = await self.repos.approval_requests.get_or_404(request_id)
            current_approvals = await self.repos.approval_decisions.count_approvals(tenant_id, request_id)
            entity = ApprovalEntity(
                id=request.id, status=ApprovalStatus(request.status), approvals_received=current_approvals,
                required_approvals=request.required_approvals, decided_at=request.decided_at,
            )

            await self.repos.approval_decisions.add(
                ApprovalDecisionModel(tenant_id=tenant_id, request_id=request_id, approver_id=approver_id, decision=decision, comment=comment)
            )

            threshold_crossed = False
            if decision == "approve":
                threshold_crossed = entity.record_approval()
            else:
                entity.reject()

            request.status = entity.status.value
            request.decided_at = entity.decided_at
            request = await self.repos.approval_requests.update(request)

            if threshold_crossed and request.target_lifecycle_stage:
                asset = await self.repos.governance_assets.get_or_404(request.asset_id)
                asset.lifecycle_stage = request.target_lifecycle_stage
                await self.repos.governance_assets.update(asset)

            await self.repos.session.commit()
            return request

    async def cancel_request(self, tenant_id: str, request_id: str) -> ApprovalRequestModel:
        request = await self.repos.approval_requests.get_or_404(request_id)
        entity = ApprovalEntity(
            id=request.id, status=ApprovalStatus(request.status), required_approvals=request.required_approvals, decided_at=request.decided_at,
        )
        entity.cancel()
        request.status = entity.status.value
        request.decided_at = entity.decided_at
        return await self.repos.approval_requests.update(request)

    async def list_pending_for_asset(self, tenant_id: str, asset_id: str) -> list[ApprovalRequestModel]:
        return await self.repos.approval_requests.list_pending_for_asset(tenant_id, asset_id)
