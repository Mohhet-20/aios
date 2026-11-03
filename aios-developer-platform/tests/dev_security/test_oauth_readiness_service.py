import pytest

from developer_platform.core.exceptions import PermissionDeniedError
from developer_platform.dev_security.oauth_readiness_service import OAuthReadinessService


def test_validate_scopes_passes_when_subset():
    service = OAuthReadinessService()
    service.validate_scopes(["read"], ["read", "write"])


def test_validate_scopes_raises_when_missing():
    service = OAuthReadinessService()
    with pytest.raises(PermissionDeniedError):
        service.validate_scopes(["admin"], ["read", "write"])


def test_wildcard_grants_everything():
    service = OAuthReadinessService()
    service.validate_scopes(["anything", "goes"], ["*"])


def test_narrow_scopes_returns_intersection():
    service = OAuthReadinessService()
    narrowed = service.narrow_scopes(["read", "write", "admin"], ["read", "write"])
    assert narrowed == ["read", "write"]


def test_narrow_scopes_with_wildcard_returns_all_requested():
    service = OAuthReadinessService()
    narrowed = service.narrow_scopes(["read", "write"], ["*"])
    assert narrowed == ["read", "write"]
