from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import ReportNotFoundError, UnsupportedReportTypeError, ValidationError
from analytics_platform.reports.report_definition_service import ReportDefinitionService

TENANT = "report-def-tenant"


@pytest.mark.asyncio
async def test_register_report_idempotent_by_name(repos):
    service = ReportDefinitionService(repos)
    a = await service.register_report(TENANT, name="Weekly Exec Summary", report_type="executive")
    b = await service.register_report(TENANT, name="Weekly Exec Summary", report_type="executive")
    assert a.id == b.id


@pytest.mark.asyncio
async def test_register_report_rejects_bad_type(repos):
    service = ReportDefinitionService(repos)
    with pytest.raises(UnsupportedReportTypeError):
        await service.register_report(TENANT, name="Bad", report_type="not_a_type")


@pytest.mark.asyncio
async def test_register_report_rejects_bad_format_and_schedule(repos):
    service = ReportDefinitionService(repos)
    with pytest.raises(ValidationError):
        await service.register_report(TENANT, name="Bad Format", report_type="usage", report_format="xml")
    with pytest.raises(ValidationError):
        await service.register_report(TENANT, name="Bad Schedule", report_type="usage", schedule="hourly")


@pytest.mark.asyncio
async def test_activate_deactivate(repos):
    service = ReportDefinitionService(repos)
    definition = await service.register_report(TENANT, name="Security Digest", report_type="security")
    deactivated = await service.deactivate(TENANT, definition.id)
    assert deactivated.status == "inactive"
    reactivated = await service.activate(TENANT, definition.id)
    assert reactivated.status == "active"


@pytest.mark.asyncio
async def test_not_found_for_other_tenant(repos):
    service = ReportDefinitionService(repos)
    definition = await service.register_report(TENANT, name="Financial Rollup", report_type="financial")
    with pytest.raises(ReportNotFoundError):
        await service.get_or_404("other-tenant", definition.id)


@pytest.mark.asyncio
async def test_list_scheduled_only_returns_active_scheduled_reports(repos):
    service = ReportDefinitionService(repos)
    daily = await service.register_report(TENANT, name="Daily Ops", report_type="operational", schedule="daily")
    await service.register_report(TENANT, name="Ad Hoc", report_type="custom", schedule="none")
    inactive_daily = await service.register_report(TENANT, name="Inactive Daily", report_type="usage", schedule="daily")
    await service.deactivate(TENANT, inactive_daily.id)

    scheduled = await service.list_scheduled(TENANT)
    scheduled_ids = {r.id for r in scheduled}
    assert daily.id in scheduled_ids
    assert inactive_daily.id not in scheduled_ids
    assert len(scheduled) == 1
