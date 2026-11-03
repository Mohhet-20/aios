"""RegistrationService: creates a new `User` in `pending_verification`
status plus its `PasswordCredentialModel` and a single-use email
verification token, all in one unit of work. The raw verification
token is returned to the caller exactly once (to be emailed) — only
its hash is ever persisted, mirroring every other token type in this
platform."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from identity_platform.authentication.password_policy import validate_password_strength
from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import ConflictError
from identity_platform.database.base import utcnow
from identity_platform.domain.enums import UserStatus
from identity_platform.models.credentials import EmailVerificationTokenModel, PasswordCredentialModel
from identity_platform.models.user import UserModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.hashing import hash_password
from identity_platform.security.tokens import generate_raw_token, hash_token


@dataclass
class RegistrationResult:
    user: UserModel
    raw_verification_token: str


class RegistrationService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def register(
        self, *, email: str, raw_password: str, display_name: str | None = None,
    ) -> RegistrationResult:
        normalized_email = email.lower().strip()
        existing = await self.repos.users.get_by_email(normalized_email)
        if existing is not None:
            raise ConflictError(f"an account already exists for '{normalized_email}'")

        validate_password_strength(raw_password, settings=self.settings)

        user = UserModel(
            email=normalized_email, status=UserStatus.PENDING_VERIFICATION.value, display_name=display_name,
        )
        await self.repos.users.add(user)

        credential = PasswordCredentialModel(
            user_id=user.id, password_hash=hash_password(raw_password), previous_password_hashes=[],
        )
        await self.repos.password_credentials.add(credential)

        raw_token = generate_raw_token()
        token = EmailVerificationTokenModel(
            user_id=user.id, token_hash=hash_token(raw_token),
            expires_at=utcnow() + timedelta(hours=self.settings.email_verification_token_ttl_hours),
        )
        await self.repos.email_verification_tokens.add(token)

        return RegistrationResult(user=user, raw_verification_token=raw_token)
