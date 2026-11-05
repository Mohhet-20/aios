"""Authentication/authorization FastAPI dependencies.

`get_current_principal` accepts either a JWT bearer token (human users) or
an `X-API-Key` header (service accounts / machine clients) and resolves both
to the same `Principal` type, matching the "OAuth-ready architecture" and
"Service Accounts" requirements — adding a third scheme (e.g. an OAuth2
authorization-code flow for a future third-party integration) means adding
one more branch here, not touching every router.
"""

from __future__ import annotations

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.database.session import get_db_session
from app.logging.context import user_id_ctx
from app.repositories.session_repository import ApiKeyRepository
from app.repositories.user_repository import UserRepository
from app.security.api_keys import hash_api_key
from app.security.jwt import TokenType, decode_token
from app.security.permissions import ROLE_PERMISSIONS, Role
from app.security.principal import Principal

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    x_api_key: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session, scope="function"),
) -> Principal:
    if x_api_key:
        return await _principal_from_api_key(x_api_key, session)
    if credentials:
        return await _principal_from_jwt(credentials.credentials, session)
    raise AuthenticationError("Missing credentials: provide a Bearer token or X-API-Key header")


async def _principal_from_jwt(token: str, session: AsyncSession) -> Principal:
    payload = decode_token(token, TokenType.ACCESS)
    user_repo = UserRepository(session)
    user = await user_repo.get(payload.sub)
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    role = Role(payload.role) if payload.role else Role.MEMBER
    permissions = {p for p in ROLE_PERMISSIONS.get(role, set())}
    user_id_ctx.set(user.id)
    return Principal(
        id=user.id,
        organization_id=payload.org_id,
        role=role,
        permissions=permissions,
        display_name=user.full_name,
    )


async def _principal_from_api_key(raw_key: str, session: AsyncSession) -> Principal:
    api_key_repo = ApiKeyRepository(session)
    key_row = await api_key_repo.get_by_hashed_key(hash_api_key(raw_key))
    if key_row is None or key_row.revoked:
        raise AuthenticationError("Invalid or revoked API key")

    role = Role.SERVICE_ACCOUNT if key_row.is_service_account else Role.MEMBER
    permissions = {p for p in ROLE_PERMISSIONS.get(role, set())}
    user_id_ctx.set(key_row.id)
    return Principal(
        id=key_row.id,
        organization_id=key_row.organization_id,
        role=role,
        permissions=permissions,
        is_service_account=True,
        display_name=key_row.name,
    )


def require_permission(permission):
    """Dependency factory: `Depends(require_permission(Permission.AGENT_WRITE))`.
    Returns the Principal so routers can also use the caller's identity
    (e.g. to stamp `created_by`) without a second dependency."""

    async def _check(principal: Principal = Depends(get_current_principal)) -> Principal:
        principal.require_permission(permission)
        return principal

    return _check


def require_role(*roles: Role):
    async def _check(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in roles:
            from app.core.exceptions import AuthorizationError

            raise AuthorizationError(f"This action requires one of roles: {[r.value for r in roles]}")
        return principal

    return _check
