"""Log retention/rotation/archiving. This build's "archiving" is
honestly scoped: `sweep_expired` hard-deletes rows past the configured
retention window in one bulk statement (the real per-tenant policy, if
set, overrides the platform default — see `RetentionPolicyRepository`).
There's no cold-storage export step here (e.g. to S3/GCS before
deletion) — that's an infrastructure integration this build doesn't
have credentials or a target to write to, so it's a disclosed gap
rather than a silently-faked one, the same posture as `NullEmailSender`
in the Collaboration Platform."""
from __future__ import annotations

from datetime import timedelta

from observability_platform.config.settings import Settings, get_settings
from observability_platform.database.base import utcnow
from observability_platform.repositories.registry import RepositoryRegistry

RESOURCE_TYPE = "logs"


class LogRetentionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def _retention_days(self, tenant_id: str) -> int:
        policy = await self.repos.retention_policies.get_for_resource(tenant_id, RESOURCE_TYPE)
        if policy is not None and policy.is_enabled:
            return policy.retention_days
        return self.settings.log_retention_days

    async def sweep_expired(self, tenant_id: str) -> int:
        retention_days = await self._retention_days(tenant_id)
        cutoff = utcnow() - timedelta(days=retention_days)
        return await self.repos.log_entries.delete_older_than(tenant_id, cutoff)
