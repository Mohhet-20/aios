import pytest

from developer_platform.core.exceptions import PermissionDeniedError
from developer_platform.dev_security.plugin_isolation_service import PluginIsolationService


def test_no_policy_allows_everything():
    service = PluginIsolationService()
    decision = service.evaluate(["network.outbound", "filesystem.read"])
    assert decision.allowed is True
    assert decision.violations == []


def test_denylist_blocks_matching_permission():
    service = PluginIsolationService()
    decision = service.evaluate(["network.outbound", "secrets.read"], denied_permissions=["secrets.read"])
    assert decision.allowed is False
    assert decision.violations == ["secrets.read"]


def test_allowlist_blocks_anything_not_listed():
    service = PluginIsolationService()
    decision = service.evaluate(["network.outbound", "filesystem.write"], allowed_permissions=["network.outbound"])
    assert decision.allowed is False
    assert decision.violations == ["filesystem.write"]


def test_assert_installable_raises_on_violation():
    service = PluginIsolationService()
    with pytest.raises(PermissionDeniedError):
        service.assert_installable(["secrets.read"], denied_permissions=["secrets.read"])


def test_assert_installable_passes_when_compliant():
    service = PluginIsolationService()
    decision = service.assert_installable(["network.outbound"], allowed_permissions=["network.outbound"])
    assert decision.allowed is True
