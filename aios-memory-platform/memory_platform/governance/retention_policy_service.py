"""RetentionPolicyService — governance-configured retention rules
(`RetentionPolicyModel`, per-workspace, optionally scoped to one
`memory_type` and/or `scope_type`) layered on top of the mechanism
`MemoryService` already provides (`apply_retention_policies`, which
sweeps entries whose `expires_at` — set from `MemoryTypePolicyModel`
defaults at creation time — has passed). This service is what lets an
admin override or add stricter/looser retention windows per workspace
without touching the built-in type defaults, and applies `action_on_expiry`
(archive/delete/summarize) rather than only ever expiring.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from memory_platform.domain.enums import RetentionAction
from memory_platform.models.governance import RetentionPolicyModel
from memory_platform.database.base import new_uuid
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.repositories.registry import RepositoryRegistry
from memory_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


class RetentionPolicyService:
    def __init__(self, repos: RepositoryRegistry, memory_service: MemoryService):
        self.repos = repos
        self.memory_service = memory_service

    async def create_policy(
        self, *, workspace_id: str, retention_days: int, action_on_expiry: RetentionAction | str, memory_type: str | None = None, scope_type: str | None = None,
    ) -> RetentionPolicyModel:
        action = action_on_expiry.value if isinstance(action_on_expiry, RetentionAction) else action_on_expiry
        return await self.repos.retention_policies.add(RetentionPolicyModel(
            id=new_uuid(), workspace_id=workspace_id, memory_type=memory_type, scope_type=scope_type,
            retention_days=retention_days, action_on_expiry=action, is_active=True,
        ))

    async def list_policies(self, workspace_id: str) -> list[RetentionPolicyModel]:
        return await self.repos.retention_policies.list_active_for_workspace(workspace_id)

    async def deactivate_policy(self, policy_id: str) -> RetentionPolicyModel:
        policy = await self.repos.retention_policies.get_or_404(policy_id)
        policy.is_active = False
        return await self.repos.retention_policies.update(policy)

    async def apply_workspace_retention_policies(self, workspace_id: str, *, actor_id: str = "system", as_of: datetime | None = None) -> dict:
        as_of = as_of or _now()
        policies = await self.repos.retention_policies.list_active_for_workspace(workspace_id)
        summary = {"policies_applied": 0, "entries_archived": 0, "entries_deleted": 0, "entries_summarized": 0}

        for policy in policies:
            cutoff = as_of - timedelta(days=policy.retention_days)
            candidates = await self.repos.memory_entries.list_older_than(workspace_id, cutoff, memory_type=policy.memory_type, scope_type=policy.scope_type)
            for entry in candidates:
                if policy.action_on_expiry == RetentionAction.ARCHIVE.value:
                    await self.memory_service.archive(entry.id, actor_id=actor_id)
                    summary["entries_archived"] += 1
                elif policy.action_on_expiry == RetentionAction.DELETE.value:
                    await self.memory_service.delete(entry.id, actor_id=actor_id)
                    summary["entries_deleted"] += 1
                elif policy.action_on_expiry == RetentionAction.SUMMARIZE.value:
                    await self.memory_service.maybe_compress(entry.id, actor_id=actor_id)
                    summary["entries_summarized"] += 1
            summary["policies_applied"] += 1
        return summary
