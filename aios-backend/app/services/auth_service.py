"""Authentication service: registration, login, token refresh/revocation.

This is one of the flagship services — real password verification, real JWT
issuance, and server-side refresh-token revocation (see `RefreshTokenModel`)
rather than a toy stateless-only JWT flow.
"""

from __future__ import annotations

from app.clock import utc_now
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.time_utils import ensure_aware_utc
from app.domain.events.events import UserLoggedIn, UserRegistered
from app.events.bus import EventBus
from app.models.session import RefreshTokenModel
from app.models.user import UserModel
from app.repositories.session_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.security.jwt import TokenType, create_access_token, create_refresh_token, decode_token
from app.security.password import hash_password, verify_password
from app.security.permissions import Role, permissions_for_role


class AuthService:
    def __init__(self, users: UserRepository, refresh_tokens: RefreshTokenRepository, event_bus: EventBus):
        self.users = users
        self.refresh_tokens = refresh_tokens
        self.event_bus = event_bus

    async def register(self, email: str, password: str, full_name: str) -> UserModel:
        existing = await self.users.get_by_email(email)
        if existing:
            raise ConflictError(f"An account with email '{email}' already exists")

        user = UserModel(email=email.lower(), full_name=full_name, hashed_password=hash_password(password))
        user = await self.users.add(user)
        await self.event_bus.publish(UserRegistered(user_id=user.id, email=user.email))
        return user

    async def authenticate(self, email: str, password: str) -> UserModel:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated")
        await self.event_bus.publish(UserLoggedIn(user_id=user.id))
        return user

    async def issue_tokens(
        self, user: UserModel, organization_id: str | None, role: Role = Role.MEMBER
    ) -> dict:
        access_token, _ = create_access_token(
            subject=user.id, org_id=organization_id, role=role.value, permissions=permissions_for_role(role)
        )
        refresh_token, jti = create_refresh_token(subject=user.id)

        from datetime import timedelta

        from app.config.settings import get_settings

        settings = get_settings()
        record = RefreshTokenModel(
            jti=jti,
            user_id=user.id,
            expires_at=utc_now() + timedelta(days=settings.refresh_token_expire_days),
        )
        await self.refresh_tokens.add(record)

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    async def refresh(
        self, refresh_token: str, organization_id: str | None, role: Role = Role.MEMBER
    ) -> dict:
        payload = decode_token(refresh_token, TokenType.REFRESH)
        stored = await self.refresh_tokens.get_by_jti(payload.jti)
        if stored is None or stored.revoked:
            raise AuthenticationError("Refresh token has been revoked or does not exist")
        if ensure_aware_utc(stored.expires_at) < utc_now():
            raise AuthenticationError("Refresh token has expired")

        user = await self.users.get_or_404(payload.sub)
        stored.revoked = True  # rotate on use: old refresh token is single-use
        await self.refresh_tokens.update(stored)
        return await self.issue_tokens(user, organization_id, role)

    async def revoke_refresh_token(self, jti: str) -> None:
        stored = await self.refresh_tokens.get_by_jti(jti)
        if stored:
            stored.revoked = True
            await self.refresh_tokens.update(stored)
