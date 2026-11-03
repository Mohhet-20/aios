"""JWT validation for the gateway's OAuth-ready architecture: issues
and verifies HS256-signed bearer tokens carrying tenant/subject/scope
claims. This is JWT issuance and validation, not a full OAuth2
authorization-code/token-exchange flow — that concern belongs to a
dedicated identity provider (in practice, the Identity Platform); this
service is what the gateway itself checks on every request that
presents a bearer token."""
from __future__ import annotations

from datetime import timedelta

import jwt

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import JwtValidationError
from gateway_platform.database.base import utcnow


class JwtService:
    def __init__(self, *, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def issue_token(
        self, *, subject: str, tenant_id: str, scopes: list[str] | None = None, ttl_minutes: int | None = None,
    ) -> str:
        now = utcnow()
        payload = {
            "sub": subject,
            "tenant_id": tenant_id,
            "scopes": scopes or [],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=ttl_minutes or self.settings.jwt_default_ttl_minutes)).timestamp()),
        }
        return jwt.encode(payload, self.settings.secret_key, algorithm=self.settings.jwt_algorithm)

    def validate_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, self.settings.secret_key, algorithms=[self.settings.jwt_algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise JwtValidationError("JWT has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise JwtValidationError(f"JWT is invalid: {exc}") from exc

    def assert_scope(self, claims: dict, required_scope: str) -> None:
        if required_scope not in claims.get("scopes", []):
            raise JwtValidationError(f"JWT is missing required scope '{required_scope}'")
