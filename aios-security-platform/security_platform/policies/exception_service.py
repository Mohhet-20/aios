"""Time-boxed policy exceptions — a carve-out for one specific resource
within a policy's scope, always expiring (never an indefinite bypass),
capped at `max_policy_exception_days` from grant time."""
from __future__ import annotations

from datetime import datetime, timedelta

from security_platform.config.settings import Settings, get_settings
from security_platform.core.exceptions import ValidationError
from security_platform.database.base import utcnow
from security_platform.domain.entities import _aware
from security_platform.models.policies import PolicyExceptionModel
from security_platform.repositories.registry import RepositoryRegistry


class PolicyExceptionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def grant_exception(
        self,
        tenant_id: str,
        policy_id: str,
        scope_ref_id: str,
        *,
        reason: str,
        expires_at: datetime,
        granted_by: str | None = None,
    ) -> PolicyExceptionModel:
        max_expiry = utcnow() + timedelta(days=self.settings.max_policy_exception_days)
        if _aware(expires_at) > max_expiry:
            raise ValidationError(
                f"Exception expiry cannot exceed {self.settings.max_policy_exception_days} days from now"
            )
        exception = PolicyExceptionModel(
            tenant_id=tenant_id, policy_id=policy_id, scope_ref_id=scope_ref_id, reason=reason,
            expires_at=expires_at, granted_by=granted_by,
        )
        return await self.repos.policy_exceptions.add(exception)

    async def revoke_exception(self, tenant_id: str, exception_id: str) -> None:
        exception = await self.repos.policy_exceptions.get_or_404(exception_id)
        await self.repos.policy_exceptions.delete(exception)

    async def is_exception_active(self, tenant_id: str, policy_id: str, scope_ref_id: str) -> bool:
        exceptions = await self.repos.policy_exceptions.list_active_for_policy(tenant_id, policy_id)
        now = utcnow()
        return any(e.scope_ref_id == scope_ref_id and _aware(e.expires_at) > now for e in exceptions)
