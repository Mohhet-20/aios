"""PasswordService: authenticated password change plus the "forgot
password" token flow. Both paths funnel through `_apply_new_password`,
which enforces the password policy and the reuse-prevention window
(`password_history_size` most-recent hashes) identically regardless of
which flow triggered the change."""
from __future__ import annotations

from datetime import timedelta

from identity_platform.authentication.password_policy import validate_password_strength
from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import (
    InvalidCredentialsError,
    PasswordPolicyError,
    TokenAlreadyUsedError,
    TokenExpiredError,
)
from identity_platform.database.base import utcnow
from identity_platform.domain.entities import _aware
from identity_platform.models.credentials import PasswordCredentialModel, PasswordResetTokenModel
from identity_platform.models.user import UserModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.hashing import hash_password, verify_password
from identity_platform.security.tokens import generate_raw_token, hash_token


class PasswordService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def _apply_new_password(self, credential: PasswordCredentialModel, raw_new_password: str) -> None:
        validate_password_strength(raw_new_password, settings=self.settings)

        if verify_password(raw_new_password, credential.password_hash) or any(
            verify_password(raw_new_password, old_hash) for old_hash in credential.previous_password_hashes
        ):
            raise PasswordPolicyError(f"new password must not match any of the last {self.settings.password_history_size} passwords")

        history = [credential.password_hash, *credential.previous_password_hashes]
        credential.previous_password_hashes = history[: self.settings.password_history_size]
        credential.password_hash = hash_password(raw_new_password)
        credential.password_updated_at = utcnow()
        credential.must_change_password = False
        await self.repos.password_credentials.update(credential)

    async def change_password(self, user_id: str, *, current_password: str, new_password: str) -> None:
        credential = await self.repos.password_credentials.get_for_user(user_id)
        if credential is None or not verify_password(current_password, credential.password_hash):
            raise InvalidCredentialsError("current password is incorrect")
        await self._apply_new_password(credential, new_password)

    async def request_reset(self, email: str, *, ip_address: str | None = None) -> str | None:
        """Returns the raw reset token, or None if no account exists for
        this email — callers must send the same generic "check your
        email" response either way, to avoid leaking account existence."""
        user = await self.repos.users.get_by_email(email)
        if user is None:
            return None
        raw_token = generate_raw_token()
        await self.repos.password_reset_tokens.add(PasswordResetTokenModel(
            user_id=user.id, token_hash=hash_token(raw_token), requested_ip=ip_address,
            expires_at=utcnow() + timedelta(minutes=self.settings.password_reset_token_ttl_minutes),
        ))
        return raw_token

    async def reset_with_token(self, raw_token: str, new_password: str) -> UserModel:
        token = await self.repos.password_reset_tokens.get_by_token_hash(hash_token(raw_token))
        if token is None:
            raise TokenExpiredError("reset token is invalid or has expired")
        if token.consumed_at is not None:
            raise TokenAlreadyUsedError("reset token has already been used")
        if _aware(token.expires_at) < utcnow():
            raise TokenExpiredError("reset token has expired")

        credential = await self.repos.password_credentials.get_for_user(token.user_id)
        if credential is None:
            raise TokenExpiredError("reset token is invalid or has expired")

        await self._apply_new_password(credential, new_password)

        token.consumed_at = utcnow()
        await self.repos.password_reset_tokens.update(token)

        return await self.repos.users.get_or_404(token.user_id)
