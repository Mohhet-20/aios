"""ApprovalPolicyService: workspace-level, optionally asset-type-scoped
rules for how many approvals a review needs and whether reviewers must
approve in order. A workspace can have a catch-all policy
(`asset_type=None`) and/or a narrower per-type override; the more
specific one wins."""
from __future__ import annotations

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.models.review import ApprovalPolicyModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class ApprovalPolicyService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_policy(
        self, workspace_id: str, *, asset_type: str | None = None, required_approvals: int | None = None,
        sequential: bool = False, auto_approve_rules: dict | None = None, created_by: str,
    ) -> ApprovalPolicyModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        return await self.repos.approval_policies.add(ApprovalPolicyModel(
            workspace_id=workspace_id, asset_type=asset_type,
            required_approvals=required_approvals or self.settings.default_required_approvals,
            sequential=sequential, auto_approve_rules=auto_approve_rules or {}, created_by=created_by,
        ))

    async def get_effective_policy(self, workspace_id: str, asset_type: str | None) -> ApprovalPolicyModel | None:
        specific = await self.repos.approval_policies.get_for_workspace_and_asset_type(workspace_id, asset_type)
        if specific is not None:
            return specific
        return await self.repos.approval_policies.get_for_workspace_and_asset_type(workspace_id, None)

    async def list_for_workspace(self, workspace_id: str) -> list[ApprovalPolicyModel]:
        return await self.repos.approval_policies.list_for_workspace(workspace_id)
