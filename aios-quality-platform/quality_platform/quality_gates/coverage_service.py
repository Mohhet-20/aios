"""Coverage snapshot recording across the nine coverage types the
prompt specifies — code, API, workflow, prompt, agent, model, dataset,
UI, integration."""
from __future__ import annotations

from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import UnsupportedCoverageTypeError
from quality_platform.models.quality_gates import CoverageSnapshotModel
from quality_platform.repositories.registry import RepositoryRegistry


class CoverageService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def record_snapshot(self, tenant_id: str, subject_ref: str, *, coverage_type: str, covered_pct: float) -> CoverageSnapshotModel:
        if coverage_type not in self.settings.coverage_types:
            raise UnsupportedCoverageTypeError(f"Unsupported coverage type '{coverage_type}'")
        snapshot = CoverageSnapshotModel(tenant_id=tenant_id, coverage_type=coverage_type, subject_ref=subject_ref, covered_pct=covered_pct)
        return await self.repos.coverage_snapshots.add(snapshot)

    async def list_for_subject(self, tenant_id: str, subject_ref: str, *, coverage_type: str | None = None, limit: int = 200) -> list[CoverageSnapshotModel]:
        return await self.repos.coverage_snapshots.list_for_subject(tenant_id, subject_ref, coverage_type=coverage_type, limit=limit)

    async def latest_pct(self, tenant_id: str, subject_ref: str, coverage_type: str) -> float | None:
        recent = await self.list_for_subject(tenant_id, subject_ref, coverage_type=coverage_type, limit=1)
        return recent[0].covered_pct if recent else None

    async def meets_target(self, tenant_id: str, subject_ref: str, coverage_type: str) -> bool:
        latest = await self.latest_pct(tenant_id, subject_ref, coverage_type)
        return latest is not None and latest >= self.settings.coverage_min_target_pct
