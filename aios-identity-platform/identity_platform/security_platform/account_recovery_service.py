"""AccountRecoveryService: administrative account recovery — distinct
from the self-service "forgot password" flow in `authentication/
password_service.py`. This is for a support/admin operator unlocking
an account that failed brute-force lockout, or force-disabling MFA
when a user has lost every recovery code and their authenticator
device. Every action here is deliberately loud: it always records a
`SecurityEventModel` so administrative recovery actions are auditable,
never silent."""
from __future__ import annotations

from identity_platform.authentication.mappers import apply_user_domain_to_model, user_to_domain
from identity_platform.domain.enums import MfaFactorStatus, SecurityEventSeverity, SecurityEventType, UserStatus
from identity_platform.models.user import UserModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security_platform.security_event_service import SecurityEventService


class AccountRecoveryService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.security_event_service = SecurityEventService(repos)

    async def admin_unlock_account(self, user_id: str, *, performed_by: str, organization_id: str | None = None) -> UserModel:
        user = await self.repos.users.get_or_404(user_id)
        entity = user_to_domain(user)
        if entity.status == UserStatus.LOCKED:
            entity.unlock()
            apply_user_domain_to_model(entity, user)
            await self.repos.users.update(user)

        await self.security_event_service.record_event(
            event_type=SecurityEventType.ACCOUNT_LOCKOUT, severity=SecurityEventSeverity.INFO,
            organization_id=organization_id, user_id=user_id,
            details={"action": "admin_unlock", "performed_by": performed_by},
        )
        return user

    async def admin_disable_mfa(self, user_id: str, *, performed_by: str, organization_id: str | None = None) -> int:
        """Force-disables every active MFA factor for a user who has
        lost access to their authenticator and every recovery code.
        Returns the number of factors disabled."""
        disabled_count = 0
        for factor in await self.repos.mfa_factors.list_for_user(user_id):
            if factor.status == MfaFactorStatus.ACTIVE.value:
                factor.status = MfaFactorStatus.DISABLED.value
                await self.repos.mfa_factors.update(factor)
                disabled_count += 1

        await self.security_event_service.record_event(
            event_type=SecurityEventType.ANOMALY, severity=SecurityEventSeverity.WARNING,
            organization_id=organization_id, user_id=user_id,
            details={"action": "admin_disable_mfa", "performed_by": performed_by, "factors_disabled": disabled_count},
        )
        return disabled_count
