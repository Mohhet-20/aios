from __future__ import annotations

import time

import pytest

from gateway_platform.api_management.jwt_service import JwtService
from gateway_platform.config.settings import Settings
from gateway_platform.core.exceptions import JwtValidationError


def _service(**overrides) -> JwtService:
    settings = Settings(secret_key="x" * 32, **overrides)
    return JwtService(settings=settings)


def test_issue_and_validate_token():
    service = _service()
    token = service.issue_token(subject="user-1", tenant_id="t1", scopes=["read"])
    claims = service.validate_token(token)
    assert claims["sub"] == "user-1"
    assert claims["tenant_id"] == "t1"
    assert claims["scopes"] == ["read"]


def test_expired_token_rejected():
    service = _service(jwt_default_ttl_minutes=0)
    token = service.issue_token(subject="user-1", tenant_id="t1", ttl_minutes=-1)
    time.sleep(0.01)
    with pytest.raises(JwtValidationError):
        service.validate_token(token)


def test_tampered_token_rejected():
    service = _service()
    token = service.issue_token(subject="user-1", tenant_id="t1")
    with pytest.raises(JwtValidationError):
        service.validate_token(token + "tampered")


def test_assert_scope():
    service = _service()
    token = service.issue_token(subject="user-1", tenant_id="t1", scopes=["read"])
    claims = service.validate_token(token)
    service.assert_scope(claims, "read")
    with pytest.raises(JwtValidationError):
        service.assert_scope(claims, "write")
