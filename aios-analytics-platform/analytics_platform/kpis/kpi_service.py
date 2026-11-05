"""KPI Engine: definitions across the seven scopes the prompt
specifies (custom, organization, workspace, engineering, ai, business,
executive), each carrying a target and optional warning/critical
thresholds plus a `higher_is_better` direction flag — without knowing
the direction, "breached" is meaningless (an error rate crossing
above its threshold is bad; an automation-rate crossing above its
threshold is good). `register_kpi` is a get-or-create by name, and
`evaluate` is the real health computation every snapshot is derived
from. `register_kpi` is guarded with an in-process `asyncio.Lock` per
`(tenant_id, scope, name)`, the same commit-spanning-lock pattern used
across every other AIOS platform's own "upsert by identity" methods,
since two concurrent callers registering the same KPI name for the
first time would otherwise both observe no existing row and both
insert, producing a duplicate KPI definition."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from analytics_platform.core.exceptions import KpiNotFoundError, ValidationError
from analytics_platform.domain.enums import KpiHealth, KpiScope
from analytics_platform.models.kpis import KpiDefinitionModel
from analytics_platform.repositories.registry import RepositoryRegistry


class KpiService:
    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_scope(self, scope: str) -> None:
        if scope not in {s.value for s in KpiScope}:
            raise ValidationError(f"'{scope}' is not a recognized KPI scope")

    async def register_kpi(
        self, tenant_id: str, *, name: str, scope: str, metric_key: str, target_value: float,
        higher_is_better: bool = True, threshold_warning: float | None = None, threshold_critical: float | None = None,
    ) -> KpiDefinitionModel:
        self._assert_valid_scope(scope)
        lock_key = f"{tenant_id}:{scope}:{name}"
        async with self._register_locks[lock_key]:
            for existing in await self.repos.kpi_definitions.list_for_tenant(tenant_id, scope=scope):
                if existing.name == name:
                    return existing
            kpi = KpiDefinitionModel(
                tenant_id=tenant_id, name=name, scope=scope, metric_key=metric_key, target_value=target_value,
                higher_is_better=higher_is_better, threshold_warning=threshold_warning, threshold_critical=threshold_critical,
                status="active",
            )
            kpi = await self.repos.kpi_definitions.add(kpi)
            # Commit while still holding the lock — releasing it before the
            # row is durably committed would reopen the exact race the lock
            # exists to close, since a waiting caller's list-and-scan would
            # run against a connection that can't yet see this insert.
            await self.repos.session.commit()
            return kpi

    async def archive_kpi(self, tenant_id: str, kpi_id: str) -> KpiDefinitionModel:
        kpi = await self.get_or_404(tenant_id, kpi_id)
        kpi.status = "archived"
        return await self.repos.kpi_definitions.update(kpi)

    async def reactivate_kpi(self, tenant_id: str, kpi_id: str) -> KpiDefinitionModel:
        kpi = await self.get_or_404(tenant_id, kpi_id)
        kpi.status = "active"
        return await self.repos.kpi_definitions.update(kpi)

    async def list_for_tenant(self, tenant_id: str, *, scope: str | None = None) -> list[KpiDefinitionModel]:
        return await self.repos.kpi_definitions.list_for_tenant(tenant_id, scope=scope)

    def evaluate_health(self, kpi: KpiDefinitionModel, current_value: float) -> str:
        """Real threshold evaluation, direction-aware: for a
        higher-is-better KPI, "breached" means the value has fallen
        *below* the critical threshold; for a lower-is-better KPI
        (error rate, cost, latency), "breached" means the value has
        risen *above* it. Falls back to `ON_TARGET` when no
        thresholds are configured."""
        if kpi.threshold_critical is not None:
            if kpi.higher_is_better and current_value < kpi.threshold_critical:
                return KpiHealth.BREACHED.value
            if not kpi.higher_is_better and current_value > kpi.threshold_critical:
                return KpiHealth.BREACHED.value
        if kpi.threshold_warning is not None:
            if kpi.higher_is_better and current_value < kpi.threshold_warning:
                return KpiHealth.AT_RISK.value
            if not kpi.higher_is_better and current_value > kpi.threshold_warning:
                return KpiHealth.AT_RISK.value
        return KpiHealth.ON_TARGET.value

    async def get_or_404(self, tenant_id: str, kpi_id: str) -> KpiDefinitionModel:
        kpi = await self.repos.kpi_definitions.get_or_404(kpi_id)
        if kpi.tenant_id != tenant_id:
            raise KpiNotFoundError(f"KPI '{kpi_id}' not found for tenant '{tenant_id}'")
        return kpi
