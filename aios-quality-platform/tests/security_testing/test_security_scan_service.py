import pytest

from quality_platform.core.exceptions import InvalidTransitionError, UnsupportedSecurityTestTypeError
from quality_platform.security_testing.security_scan_service import SecurityScanService

pytestmark = pytest.mark.asyncio


async def test_request_scan_rejects_unsupported_type(repos):
    svc = SecurityScanService(repos)
    with pytest.raises(UnsupportedSecurityTestTypeError):
        await svc.request_scan("t1", security_test_type="not-a-type", target_ref="svc:1")


async def test_start_and_finish_scan_no_findings(repos):
    svc = SecurityScanService(repos)
    scan = await svc.request_scan("t1", security_test_type="authentication", target_ref="svc:1")
    await svc.start("t1", scan.id)
    finished = await svc.finish_scan("t1", scan.id)
    assert finished.status == "completed"
    assert finished.result["total_findings"] == 0
    assert finished.result["blocks_gate"] is False


async def test_cannot_complete_without_start(repos):
    svc = SecurityScanService(repos)
    scan = await svc.request_scan("t1", security_test_type="rbac", target_ref="svc:1")
    with pytest.raises(InvalidTransitionError):
        await svc.complete("t1", scan.id, result={})


async def test_critical_finding_blocks_gate_when_setting_enabled(repos):
    svc = SecurityScanService(repos)
    scan = await svc.request_scan("t1", security_test_type="secrets", target_ref="svc:2")
    await svc.start("t1", scan.id)
    await svc.record_finding("t1", scan.id, severity="critical", title="hardcoded API key", description="found in config")
    await svc.record_finding("t1", scan.id, severity="low", title="verbose error message")

    finished = await svc.finish_scan("t1", scan.id)
    assert finished.result["blocks_gate"] is True
    assert finished.result["findings_by_severity"]["critical"] == 1
    assert finished.result["total_findings"] == 2


async def test_low_severity_finding_does_not_block_gate(repos):
    svc = SecurityScanService(repos)
    scan = await svc.request_scan("t1", security_test_type="dependency_scan", target_ref="svc:3")
    await svc.start("t1", scan.id)
    await svc.record_finding("t1", scan.id, severity="low", title="outdated dependency")
    finished = await svc.finish_scan("t1", scan.id)
    assert finished.result["blocks_gate"] is False


async def test_fail_scan(repos):
    svc = SecurityScanService(repos)
    scan = await svc.request_scan("t1", security_test_type="jailbreak", target_ref="svc:4")
    await svc.start("t1", scan.id)
    failed = await svc.fail("t1", scan.id, error="scanner crashed")
    assert failed.status == "failed"


async def test_list_scans_filters_by_type(repos):
    svc = SecurityScanService(repos)
    await svc.request_scan("t1", security_test_type="compliance", target_ref="svc:5")
    await svc.request_scan("t1", security_test_type="container_security", target_ref="svc:6")
    compliance_only = await svc.list_scans("t1", security_test_type="compliance")
    assert len(compliance_only) == 1
