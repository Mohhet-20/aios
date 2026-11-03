"""Security scan lifecycle. Status is a simple field guarded directly
here rather than through a dedicated domain entity — this is one of
the two "simple status field" resources this platform's domain layer
deliberately skipped (see `domain/entities.py`'s module docstring),
since its queued -> running -> completed/failed shape carries no extra
domain logic beyond the four states themselves. Reuses the shared
`JobStatus` enum rather than declaring a scan-specific one, for the
same reason. finish_scan() is the convenience orchestrator: it tallies
recorded findings by severity and flags `blocks_gate` when
`security_critical_finding_blocks_gate` is set and a critical finding
was recorded."""
from __future__ import annotations


from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import InvalidTransitionError, SecurityScanNotFoundError, UnsupportedSecurityTestTypeError
from quality_platform.domain.enums import JobStatus
from quality_platform.models.security_testing import SecurityFindingModel, SecurityScanModel
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.clock import utc_now

_SCAN_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.RUNNING},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
}


class SecurityScanService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, scan_id: str) -> SecurityScanModel:
        scan = await self.repos.security_scans.get_or_404(scan_id)
        if scan.tenant_id != tenant_id:
            raise SecurityScanNotFoundError(f"Security scan '{scan_id}' not found for tenant '{tenant_id}'")
        return scan

    async def request_scan(self, tenant_id: str, *, security_test_type: str, target_ref: str) -> SecurityScanModel:
        if security_test_type not in self.settings.security_test_types:
            raise UnsupportedSecurityTestTypeError(f"Unsupported security test type '{security_test_type}'")
        scan = SecurityScanModel(tenant_id=tenant_id, security_test_type=security_test_type, target_ref=target_ref, status=JobStatus.QUEUED.value)
        return await self.repos.security_scans.add(scan)

    async def _transition(self, tenant_id: str, scan_id: str, target: JobStatus) -> SecurityScanModel:
        scan = await self.get_or_404(tenant_id, scan_id)
        current = JobStatus(scan.status)
        if target not in _SCAN_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(f"SecurityScan '{scan_id}' cannot transition from {current.value} to {target.value}")
        scan.status = target.value
        return scan

    async def start(self, tenant_id: str, scan_id: str) -> SecurityScanModel:
        scan = await self._transition(tenant_id, scan_id, JobStatus.RUNNING)
        return await self.repos.security_scans.update(scan)

    async def complete(self, tenant_id: str, scan_id: str, *, result: dict) -> SecurityScanModel:
        scan = await self._transition(tenant_id, scan_id, JobStatus.COMPLETED)
        scan.result = result
        scan.completed_at = utc_now()
        return await self.repos.security_scans.update(scan)

    async def fail(self, tenant_id: str, scan_id: str, *, error: str) -> SecurityScanModel:
        scan = await self._transition(tenant_id, scan_id, JobStatus.FAILED)
        scan.error = error
        scan.completed_at = utc_now()
        return await self.repos.security_scans.update(scan)

    async def record_finding(
        self, tenant_id: str, scan_id: str, *, severity: str, title: str, description: str = ""
    ) -> SecurityFindingModel:
        await self.get_or_404(tenant_id, scan_id)
        finding = SecurityFindingModel(tenant_id=tenant_id, security_scan_id=scan_id, severity=severity, title=title, description=description)
        return await self.repos.security_findings.add(finding)

    async def list_findings(self, tenant_id: str, scan_id: str) -> list[SecurityFindingModel]:
        return await self.repos.security_findings.list_for_scan(tenant_id, scan_id)

    async def finish_scan(self, tenant_id: str, scan_id: str) -> SecurityScanModel:
        findings = await self.list_findings(tenant_id, scan_id)
        by_severity: dict[str, int] = {}
        for f in findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        has_critical = by_severity.get("critical", 0) > 0
        blocks_gate = has_critical and self.settings.security_critical_finding_blocks_gate
        result = {"findings_by_severity": by_severity, "total_findings": len(findings), "blocks_gate": blocks_gate}
        return await self.complete(tenant_id, scan_id, result=result)

    async def list_scans(self, tenant_id: str, *, security_test_type: str | None = None, limit: int = 100) -> list[SecurityScanModel]:
        return await self.repos.security_scans.list_for_tenant(tenant_id, security_test_type=security_test_type, limit=limit)
