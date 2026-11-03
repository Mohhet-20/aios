import pytest

from tool_platform.core.exceptions import CredentialError
from tool_platform.credentials.token_injection import build_auth_headers


def test_api_key_default_header():
    assert build_auth_headers("api_key", {"api_key": "abc123"}) == {"X-Api-Key": "abc123"}


def test_api_key_custom_header_name():
    assert build_auth_headers("api_key", {"api_key": "abc123", "header_name": "X-Custom-Key"}) == {"X-Custom-Key": "abc123"}


def test_oauth2_bearer():
    assert build_auth_headers("oauth2", {"access_token": "tok"}) == {"Authorization": "Bearer tok"}


def test_bearer_token_type():
    assert build_auth_headers("bearer_token", {"token": "tok"}) == {"Authorization": "Bearer tok"}


def test_jwt_bearer():
    assert build_auth_headers("jwt", {"access_token": "eyJ..."}) == {"Authorization": "Bearer eyJ..."}


def test_oauth2_missing_token_raises():
    with pytest.raises(CredentialError):
        build_auth_headers("oauth2", {})


def test_service_account():
    assert build_auth_headers("service_account", {"token": "svc-tok"}) == {"Authorization": "Bearer svc-tok"}


def test_managed_returns_empty():
    assert build_auth_headers("managed", {"connection_string": "postgres://..."}) == {}


def test_unsupported_type_raises():
    with pytest.raises(Exception):
        build_auth_headers("not-a-type", {})
