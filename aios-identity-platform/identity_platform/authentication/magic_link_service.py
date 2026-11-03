"""MagicLinkService: passwordless sign-in via a single-use, short-lived
emailed link. Unlike the password-reset token (bound to the user's
current email on file), the magic-link token also carries the email it
was requested for, so a user changing their primary email mid-flight
doesn't silently redeem a stale link against the wrong address."""
from __future__ import annotations

from datetime import timedelta

from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import NotFoundError, TokenAlreadyUsedError, TokenExpiredError
from identity_platform.database.base import utcnow
from identity_platform.domain.entities import _aware
from identity_platform.models.credentials import MagicLinkTokenModel
from identity_platform.models.user import UserModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.tokens import generate_raw_token, hash_token


class MagicLinkService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def request_link(self, email: str) -> str | None:
        normalized_email = email.lower().strip()
        user = await self.repos.users.get_by_email(normalized_email)
        if user is None:
            return None
        raw_token = generate_raw_token()
        await self.repos.magic_link_tokens.add(MagicLinkTokenModel(
            user_id=user.id, email=normalized_email, token_hash=hash_token(raw_token),
            expires_at=utcnow() + timedelta(minutes=self.settings.magic_link_token_ttl_minutes),
        ))
        return raw_token

    async def redeem(self, raw_token: str) -> UserModel:
        token = await self.repos.magic_link_tokens.get_by_token_hash(hash_token(raw_token))
        if token is None:
            raise TokenExpiredError("magic link is invalid or has expired")
        if token.consumed_at is not None:
            raise TokenAlreadyUsedError("magic link has already been used")
        if _aware(token.expires_at) < utcnow():
            raise TokenExpiredError("magic link has expired")

        user = await self.repos.users.get(token.user_id)
        if user is None or user.email != token.email:
            raise NotFoundError("magic link no longer matches an active account")

        token.consumed_at = utcnow()
        await self.repos.magic_link_tokens.update(token)
        user.last_login_at = utcnow()
        await self.repos.users.update(user)
        return user
