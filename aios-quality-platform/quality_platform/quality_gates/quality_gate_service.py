"""Quality gate management: `create_gate` is a get-or-create upsert
keyed on (tenant_id, release_ref, name) behind a commit-spanning
`asyncio.Lock` — the same pattern established across every prior AIOS
platform, with the mid-lock commit needed so a waiting caller's read
can't observe a still-uncommitted insert from a separate DB
connection. record_check() logs one of the eight check types'
pass/fail outcome; evaluate_gate() scores the gate as the percentage
of recorded checks that passed and marks it passed/failed against
`min_score` (defaulting to `quality_gate_min_score`) -- a gate with no
recorded checks at all scores 0 and fails closed, since "no evidence"
is not the same as "passing evidence"."""
from __future__ import annotations


import asyncio
from collections import defaultdict

from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import QualityGateError, QualityGateFailedError, QualityGateNotFoundError
from quality_platform.domain.enums import QualityGateStatus
from quality_platform.models.quality_gates import QualityGateCheckResultModel, QualityGateModel
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.clock import utc_now


class QualityGateService:
    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, gate_id: str) -> QualityGateModel:
        gate = await self.repos.quality_gates.get_or_404(gate_id)
        if gate.tenant_id != tenant_id:
            raise QualityGateNotFoundError(f"Quality gate '{gate_id}' not found for tenant '{tenant_id}'")
        return gate

    async def create_gate(self, tenant_id: str, *, name: str, release_ref: str, min_score: float | None = None) -> QualityGateModel:
        lock_key = f"{tenant_id}:{release_ref}:{name}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.quality_gates.get_for_release(tenant_id, release_ref, name)
            if existing is not None:
                return existing
            gate = QualityGateModel(
                tenant_id=tenant_id, name=name, release_ref=release_ref,
                min_score=min_score if min_score is not None else self.settings.quality_gate_min_score,
                status=QualityGateStatus.PENDING.value,
            )
            gate = await self.repos.quality_gates.add(gate)
            await self.repos.session.commit()
            return gate

    async def record_check(
        self, tenant_id: str, gate_id: str, *, check_type: str, passed: bool, details: dict | None = None
    ) -> QualityGateCheckResultModel:
        if check_type not in self.settings.quality_gate_check_types:
            raise QualityGateError(f"Unsupported quality gate check type '{check_type}'")
        await self.get_or_404(tenant_id, gate_id)
        check = QualityGateCheckResultModel(tenant_id=tenant_id, quality_gate_id=gate_id, check_type=check_type, passed=passed, details=details or {})
        return await self.repos.quality_gate_check_results.add(check)

    async def list_checks(self, tenant_id: str, gate_id: str) -> list[QualityGateCheckResultModel]:
        return await self.repos.quality_gate_check_results.list_for_gate(tenant_id, gate_id)

    async def evaluate_gate(self, tenant_id: str, gate_id: str) -> QualityGateModel:
        gate = await self.get_or_404(tenant_id, gate_id)
        checks = await self.list_checks(tenant_id, gate_id)
        total = len(checks)
        score = (sum(1 for c in checks if c.passed) / total * 100.0) if total > 0 else 0.0
        gate.status = QualityGateStatus.PASSED.value if score >= gate.min_score else QualityGateStatus.FAILED.value
        gate.evaluated_at = utc_now()
        return await self.repos.quality_gates.update(gate)

    async def waive_gate(self, tenant_id: str, gate_id: str) -> QualityGateModel:
        gate = await self.get_or_404(tenant_id, gate_id)
        gate.status = QualityGateStatus.WAIVED.value
        gate.evaluated_at = utc_now()
        return await self.repos.quality_gates.update(gate)

    def assert_gate_passed(self, gate: QualityGateModel) -> None:
        if gate.status not in (QualityGateStatus.PASSED.value, QualityGateStatus.WAIVED.value):
            raise QualityGateFailedError(f"Quality gate '{gate.id}' is '{gate.status}', not passed or waived")

    async def list_gates(self, tenant_id: str, *, release_ref: str | None = None) -> list[QualityGateModel]:
        return await self.repos.quality_gates.list_for_tenant(tenant_id, release_ref=release_ref)
