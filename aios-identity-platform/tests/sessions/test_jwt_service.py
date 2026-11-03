import time

import pytest

from identity_platform.config.settings import Settings
from identity_platform.core.exceptions import TokenError, TokenExpiredError
from identity_platform.sessions.jwt_service import JwtService


def test_issue_and_decode_access_token():
    service = JwtService(settings=Settings(secret_key="x" * 32))
    token = service.issue_access_token(user_id="user-1", session_id="sess-1", organization_id="org-1")

    payload = service.decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["sid"] == "sess-1"
    assert payload["org"] == "org-1"


def test_decode_rejects_garbage_token():
    service = JwtService(settings=Settings(secret_key="x" * 32))
    with pytest.raises(TokenError):
        service.decode_access_token("not-a-real-jwt")


def test_decode_rejects_expired_token():
    settings = Settings(secret_key="x" * 32, jwt_access_token_ttl_seconds=1)
    service = JwtService(settings=settings)
    token = service.issue_access_token(user_id="user-1", session_id="sess-1")
    time.sleep(2)
    with pytest.raises(TokenExpiredError):
        service.decode_access_token(token)


def test_decode_rejects_token_signed_with_different_key():
    a = JwtService(settings=Settings(secret_key="a" * 32))
    b = JwtService(settings=Settings(secret_key="b" * 32))
    token = a.issue_access_token(user_id="user-1", session_id="sess-1")
    with pytest.raises(TokenError):
        b.decode_access_token(token)
