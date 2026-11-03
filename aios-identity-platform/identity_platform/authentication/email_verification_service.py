"""EmailVerificationService: redeem the single-use token issued at
registration (or a fresh re-send) and transition the user out of
`pending_verification` via the domain entity's guarded `verify_email()`."""
from __future__ import annotations

from datetime import timedelta

from identity_platform.authentication.mappers import apply_user_domain_to_model, user_to_domain
from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import TokenAlreadyUsedError, TokenExpiredError
from identity_platform.database.base import utcnow
from identity_platform.domain.entities import _aware
from identity_platform.models.credentials import EmailVerificationTokenModel
from identity_platform.models.user import UserModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.tokens import generate_raw_token, hash_token


class EmailVerificationService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def request_verification(self, user_id: str) -> str:
        """Issues a fresh token (does not invalidate prior unexpired ones —
        any still-valid token remains usable, matching typical "resend
        verification email" behavior)."""
        raw_token = generate_raw_token()
        token = EmailVerificationTokenModel(
            user_id=user_id, token_hash=hash_token(raw_token),
            expires_at=utcnow() + timedelta(hours=self.settings.email_verification_token_ttl_hours),
        )
        await self.repos.email_verification_tokens.add(token)
        return raw_token

    async def verify(self, raw_token: str) -> UserModel:
        token = await self.repos.email_verification_tokens.get_by_token_hash(hash_token(raw_token))
        if token is None:
            raise TokenExpiredError("verification token is invalid or has expired")
        if token.consumed_at is not None:
            raise TokenAlreadyUsedError("verification token has already been used")
        if _aware(token.expires_at) < utcnow():
            raise TokenExpiredError("verification token has expired")

        user_model = await self.repos.users.get_or_404(token.user_id)
        entity = user_to_domain(user_model)
        entity.verify_email()
        apply_user_domain_to_model(entity, user_model)
        await self.repos.users.update(user_model)

        token.consumed_at = utcnow()
        await self.repos.email_verification_tokens.update(token)
        return user_model
