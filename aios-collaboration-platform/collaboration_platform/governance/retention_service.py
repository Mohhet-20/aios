"""RetentionService: per-workspace, per-resource-type retention
policies and an idempotent sweep that hard-deletes soft-deleted assets
past their retention window — safe to call repeatedly (already-purged
rows simply won't match the sweep query again), mirroring the
Identity Platform's `SessionService.sweep_expirations` idempotent-sweep
precedent."""
from __future__ import annotations

from datetime import timedelta

from collaboration_platform.database.base import utcnow
from collaboration_platform.domain.enums import AssetStatus
from collaboration_platform.models.governance import RetentionPolicyModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class RetentionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def set_policy(self, workspace_id: str, *, resource_type: str, retain_days: int, created_by: str, applies_to_deleted_only: bool = True) -> RetentionPolicyModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        existing = await self.repos.retention_policies.get_for_workspace_and_type(workspace_id, resource_type)
        if existing is not None:
            existing.retain_days = retain_days
            existing.applies_to_deleted_only = applies_to_deleted_only
            return await self.repos.retention_policies.update(existing)
        return await self.repos.retention_policies.add(RetentionPolicyModel(
            workspace_id=workspace_id, resource_type=resource_type, retain_days=retain_days,
            applies_to_deleted_only=applies_to_deleted_only, created_by=created_by,
        ))

    async def sweep_expired_assets(self, workspace_id: str) -> list[str]:
        """Hard-deletes `CollaborationAssetModel` rows that are already
        soft-deleted (status=DELETED) and past this workspace's asset
        retention window. Returns the ids purged. Assets with no
        matching policy are left untouched — retention is opt-in, not
        a default-on background deletion."""
        policy = await self.repos.retention_policies.get_for_workspace_and_type(workspace_id, "asset")
        if policy is None:
            return []
        cutoff = utcnow() - timedelta(days=policy.retain_days)
        assets = await self.repos.assets.list_for_workspace(workspace_id, status=AssetStatus.DELETED.value)
        purged = []
        for asset in assets:
            if asset.deleted_at is not None and asset.deleted_at < cutoff:
                await self.repos.assets.delete(asset, hard=True)
                purged.append(asset.id)
        return purged

    async def list_for_workspace(self, workspace_id: str) -> list[RetentionPolicyModel]:
        return await self.repos.retention_policies.list_for_workspace(workspace_id)
