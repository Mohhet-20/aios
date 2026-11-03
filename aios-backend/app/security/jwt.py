"""JWT access/refresh token issuance and verification.

Access tokens are short-lived and carry the principal's identity + role for
fast in-process authorization checks without a DB round trip. Refresh tokens
are long-lived, opaque-to-the-client-otherwise, and are additionally checked
against the `RefreshToken` table (see `app.models.session`) so they can be
revoked server-side — a bare JWT refresh token can't be revoked before
expiry, which is why AIOS persists them.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

import jwt
from pydantic import BaseModel

from app.clock import utc_now
from app.config.settings import get_settings
from app.core.exceptions import AuthenticationError


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    sub: str  # user id
    type: TokenType
    org_id: str | None = None
    role: str | None = None
    permissions: list[str] = []
    jti: str
    exp: datetime
    iat: datetime


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    org_id: str | None = None,
    role: str | None = None,
    permissions: list[str] | None = None,
) -> tuple[str, str]:
    settings = get_settings()
    now = utc_now()
    jti = uuid4().hex
    payload = {
        "sub": subject,
        "type": token_type.value,
        "org_id": org_id,
        "role": role,
        "permissions": permissions or [],
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, jti


def create_access_token(
    subject: str, org_id: str | None, role: str | None, permissions: list[str]
) -> tuple[str, str]:
    settings = get_settings()
    return _create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes),
        org_id=org_id,
        role=role,
        permissions=permissions,
    )


def create_refresh_token(subject: str) -> tuple[str, str]:
    settings = get_settings()
    return _create_token(subject, TokenType.REFRESH, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    settings = get_settings()
    try:
        raw = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    payload = TokenPayload.model_validate(raw)
    if payload.type != expected_type:
        raise AuthenticationError(f"Expected a {expected_type.value} token")
    return payload
