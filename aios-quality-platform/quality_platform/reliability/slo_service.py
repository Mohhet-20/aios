"""SLO definition management. `register_slo` is a get-or-create upsert
keyed on (tenant_id, name) behind a commit-spanning `asyncio.Lock` —
the same pattern established across every other AIOS platform, with
the mid-lock commit needed so a waiting caller's read can't observe a
still-uncommitted insert from a separate DB connection. evaluate_slo()
pulls the service's latest recorded "availability" snapshot (or an
explicitly supplied current reading) and classifies/persists the SLO's
status via `slo_rules`."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import SloNotFoundError, ValidationError
from quality_platform.models.reliability import SloDefinitionModel
from quality_platform.reliability.reliability_snapshot_service import ReliabilitySnapshotService
from quality_platform.reliability.slo_rules import classify_slo_status, compute_error_budget_remaining_pct
from quality_platform.repositories.registry import RepositoryRegistry


class SloService:
    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()
        self.snapshots = ReliabilitySnapshotService(repos)

    async def get_or_404(self, tenant_id: str, slo_id: str) -> SloDefinitionModel:
        slo = await self.repos.slo_definitions.get_or_404(slo_id)
        if slo.tenant_id != tenant_id:
            raise SloNotFoundError(f"SLO '{slo_id}' not found for tenant '{tenant_id}'")
        return slo

    async def register_slo(
        self, tenant_id: str, *, name: str, service_ref: str, target_pct: float | None = None, window_days: int | None = None
    ) -> SloDefinitionModel:
        lock_key = f"{tenant_id}:{name}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.slo_definitions.get_by_name(tenant_id, name)
            if existing is not None:
                return existing
            slo = SloDefinitionModel(
                tenant_id=tenant_id, name=name, service_ref=service_ref,
                target_pct=target_pct if target_pct is not None else self.settings.reliability_default_slo_target,
                window_days=window_days if window_days is not None else self.settings.reliability_error_budget_window_days,
                status="meeting",
            )
            slo = await self.repos.slo_definitions.add(slo)
            await self.repos.session.commit()
            return slo

    async def evaluate_slo(self, tenant_id: str, slo_id: str, *, current_pct: float | None = None) -> SloDefinitionModel:
        slo = await self.get_or_404(tenant_id, slo_id)
        if current_pct is None:
            current_pct = await self.snapshots.latest_value(tenant_id, slo.service_ref, "availability")
        if current_pct is None:
            raise ValidationError(f"No availability snapshot recorded for service '{slo.service_ref}'")
        slo.status = classify_slo_status(current_pct, slo.target_pct).value
        return await self.repos.slo_definitions.update(slo)

    async def error_budget_remaining_pct(self, tenant_id: str, slo_id: str, *, current_pct: float) -> float:
        slo = await self.get_or_404(tenant_id, slo_id)
        return compute_error_budget_remaining_pct(current_pct, slo.target_pct)

    async def list_slos(self, tenant_id: str, *, service_ref: str | None = None) -> list[SloDefinitionModel]:
        return await self.repos.slo_definitions.list_for_tenant(tenant_id, service_ref=service_ref)
