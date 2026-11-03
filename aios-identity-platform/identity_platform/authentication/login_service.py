"""LoginService: verifies email/password credentials, enforces account
lockout / brute-force protection (via the `User` domain entity's
guarded lock/unlock transitions), and records every attempt — success
or failure — to the append-only `LoginHistoryModel`, the record a
future risk-scoring pass (Security Platform) reads. Deliberately does
NOT issue a session/JWT itself — that is Session Management's job
(`sessions/session_service.py`); this service's contract is "are these
credentials good, and is this account allowed to log in right now,"
returning the authenticated `UserModel` on success."""
from __future__ import annotations

from datetime import timedelta

from identity_platform.authentication.mappers import apply_user_domain_to_model, user_to_domain
from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import AccountLockedError, AccountNotVerifiedError, InvalidCredentialsError
from identity_platform.database.base import utcnow
from identity_platform.domain.enums import UserStatus
from identity_platform.models.session import LoginHistoryModel
from identity_platform.models.user import UserModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.hashing import verify_password


class LoginService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def authenticate(
        self, *, email: str, raw_password: str, ip_address: str | None = None, user_agent: str | None = None,
    ) -> UserModel:
        normalized_email = email.lower().strip()
        user_model = await self.repos.users.get_by_email(normalized_email)

        if user_model is None:
            await self._record_attempt(normalized_email, user_id=None, success=False, failure_reason="no_such_user", ip_address=ip_address, user_agent=user_agent)
            raise InvalidCredentialsError("email or password is incorrect")

        entity = user_to_domain(user_model)

        if entity.status == UserStatus.LOCKED:
            if entity.locked_until is not None and entity.locked_until <= utcnow():
                entity.unlock()
                apply_user_domain_to_model(entity, user_model)
                await self.repos.users.update(user_model)
            else:
                await self._record_attempt(normalized_email, user_id=user_model.id, success=False, failure_reason="account_locked", ip_address=ip_address, user_agent=user_agent)
                raise AccountLockedError("account is temporarily locked due to repeated failed logins")

        credential = await self.repos.password_credentials.get_for_user(user_model.id)
        password_ok = credential is not None and verify_password(raw_password, credential.password_hash)

        if not password_ok:
            crossed_threshold = entity.record_failed_login(threshold=self.settings.account_lockout_threshold)
            if crossed_threshold:
                entity.lock(until=utcnow() + timedelta(minutes=self.settings.account_lockout_duration_minutes))
            apply_user_domain_to_model(entity, user_model)
            await self.repos.users.update(user_model)
            await self._record_attempt(normalized_email, user_id=user_model.id, success=False, failure_reason="bad_password", ip_address=ip_address, user_agent=user_agent)
            if entity.status == UserStatus.LOCKED:
                raise AccountLockedError("account has been locked due to repeated failed logins")
            raise InvalidCredentialsError("email or password is incorrect")

        if entity.status == UserStatus.PENDING_VERIFICATION:
            await self._record_attempt(normalized_email, user_id=user_model.id, success=False, failure_reason="email_not_verified", ip_address=ip_address, user_agent=user_agent)
            raise AccountNotVerifiedError("email address has not been verified yet")

        if entity.status != UserStatus.ACTIVE:
            await self._record_attempt(normalized_email, user_id=user_model.id, success=False, failure_reason=f"status_{entity.status.value}", ip_address=ip_address, user_agent=user_agent)
            raise InvalidCredentialsError("account is not active")

        entity.reset_failed_logins()
        apply_user_domain_to_model(entity, user_model)
        user_model.last_login_at = utcnow()
        await self.repos.users.update(user_model)

        await self._record_attempt(normalized_email, user_id=user_model.id, success=True, failure_reason=None, ip_address=ip_address, user_agent=user_agent)
        return user_model

    async def _record_attempt(
        self, email: str, *, user_id: str | None, success: bool, failure_reason: str | None,
        ip_address: str | None, user_agent: str | None,
    ) -> None:
        await self.repos.login_history.add(LoginHistoryModel(
            user_id=user_id, email_attempted=email, success=success, failure_reason=failure_reason,
            ip_address=ip_address, user_agent=user_agent,
        ))

    async def is_rate_limited(self, email: str) -> bool:
        """Brute-force guard independent of account lockout — counts
        recent failures against this email within the lockout window,
        even if they never resolved to a real user (so an attacker
        probing unknown emails is still throttled)."""
        since = utcnow() - timedelta(minutes=self.settings.account_lockout_window_minutes)
        failures = await self.repos.login_history.count_recent_failures(email.lower().strip(), since=since)
        return failures >= self.settings.account_lockout_threshold
