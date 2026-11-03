"""Report definition management: register (get-or-create by name),
list, activate/deactivate, and find due-for-schedule report configs.
Mirrors the register/list/activate/deactivate shape used by every
prior AIOS platform's "config catalog" resources (connectors,
policies, KPI/metric definitions in this platform). `register_report`
is guarded with an in-process `asyncio.Lock` per `(tenant_id,
report_type, name)`, the same commit-spanning-lock pattern used
across every prior AIOS platform's own "upsert by identity" methods,
since two concurrent callers registering the same report name for the
first time would otherwise both observe no existing row and both
insert, producing a duplicate report definition."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from analytics_platform.core.exceptions import ReportNotFoundError, UnsupportedReportTypeError, ValidationError
from analytics_platform.domain.enums import ReportFormat, ReportSchedule, ReportType
from analytics_platform.models.reports import ReportDefinitionModel
from analytics_platform.repositories.registry import RepositoryRegistry


class ReportDefinitionService:
    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid(self, *, report_type: str, report_format: str, schedule: str) -> None:
        if report_type not in {t.value for t in ReportType}:
            raise UnsupportedReportTypeError(f"'{report_type}' is not a recognized report type")
        if report_format not in {f.value for f in ReportFormat}:
            raise ValidationError(f"'{report_format}' is not a recognized report format")
        if schedule not in {s.value for s in ReportSchedule}:
            raise ValidationError(f"'{schedule}' is not a recognized report schedule")

    async def register_report(
        self, tenant_id: str, *, name: str, report_type: str, report_format: str = "json",
        schedule: str = "none", config: dict | None = None,
    ) -> ReportDefinitionModel:
        self._assert_valid(report_type=report_type, report_format=report_format, schedule=schedule)
        lock_key = f"{tenant_id}:{report_type}:{name}"
        async with self._register_locks[lock_key]:
            for existing in await self.repos.report_definitions.list_for_tenant(tenant_id, report_type=report_type):
                if existing.name == name:
                    return existing
            definition = ReportDefinitionModel(
                tenant_id=tenant_id, name=name, report_type=report_type, report_format=report_format,
                schedule=schedule, config=config or {}, status="active",
            )
            definition = await self.repos.report_definitions.add(definition)
            # Commit while still holding the lock — releasing it before the
            # row is durably committed would reopen the exact race the lock
            # exists to close, since a waiting caller's list-and-scan would
            # run against a connection that can't yet see this insert.
            await self.repos.session.commit()
            return definition

    async def get_or_404(self, tenant_id: str, definition_id: str) -> ReportDefinitionModel:
        definition = await self.repos.report_definitions.get_or_404(definition_id)
        if definition.tenant_id != tenant_id:
            raise ReportNotFoundError(f"Report definition '{definition_id}' not found for tenant '{tenant_id}'")
        return definition

    async def list_for_tenant(self, tenant_id: str, *, report_type: str | None = None) -> list[ReportDefinitionModel]:
        return await self.repos.report_definitions.list_for_tenant(tenant_id, report_type=report_type)

    async def list_scheduled(self, tenant_id: str) -> list[ReportDefinitionModel]:
        return await self.repos.report_definitions.list_scheduled(tenant_id)

    async def activate(self, tenant_id: str, definition_id: str) -> ReportDefinitionModel:
        definition = await self.get_or_404(tenant_id, definition_id)
        definition.status = "active"
        return await self.repos.report_definitions.update(definition)

    async def deactivate(self, tenant_id: str, definition_id: str) -> ReportDefinitionModel:
        definition = await self.get_or_404(tenant_id, definition_id)
        definition.status = "inactive"
        return await self.repos.report_definitions.update(definition)
