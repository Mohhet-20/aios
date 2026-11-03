"""JwtService: short-lived, stateless JWT access tokens (`pyjwt`), kept
deliberately separate from the long-lived, stateful, hashed-at-rest
refresh token that backs `SessionModel`. The access token carries just
enough claims (`sub`, `sid`, `org`) for a downstream service to
authorize a request without a database round trip; the refresh token
is the only thing that can be revoked, which is why session revocation
lives in `session_service.py`, not here."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

import jwt

from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import TokenError, TokenExpiredError
from identity_platform.database.base import utcnow


class JwtService:
    def __init__(self, *, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def issue_access_token(self, *, user_id: str, session_id: str, organization_id: str | None = None) -> str:
        now = utcnow()
        payload: dict[str, Any] = {
            "sub": user_id,
            "sid": session_id,
            "org": organization_id,
            "iat": now,
            "exp": now + timedelta(seconds=self.settings.jwt_access_token_ttl_seconds),
        }
        return jwt.encode(payload, self.settings.secret_key, algorithm=self.settings.jwt_algorithm)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self.settings.secret_key, algorithms=[self.settings.jwt_algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError("access token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise TokenError("access token is invalid") from exc
