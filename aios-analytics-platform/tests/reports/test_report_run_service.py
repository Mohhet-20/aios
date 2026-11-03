from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import ReportGenerationFailedError, ValidationError
from analytics_platform.reports.report_definition_service import ReportDefinitionService
from analytics_platform.reports.report_run_service import ReportRunService

TENANT = "report-run-tenant"


@pytest.mark.asyncio
async def test_request_run_requires_active_definition(repos):
    definitions = ReportDefinitionService(repos)
    runs = ReportRunService(repos)
    definition = await definitions.register_report(TENANT, name="Usage Report", report_type="usage")
    await definitions.deactivate(TENANT, definition.id)
    with pytest.raises(ValidationError):
        await runs.request_run(TENANT, definition.id)


@pytest.mark.asyncio
async def test_full_run_lifecycle_completes_with_payload(repos):
    definitions = ReportDefinitionService(repos)
    runs = ReportRunService(repos)
    definition = await definitions.register_report(TENANT, name="Ops Digest", report_type="operational")

    run = await runs.request_run(TENANT, definition.id)
    assert run.status == "queued"

    completed = await runs.generate(TENANT, run.id)
    assert completed.status == "completed"
    assert completed.completed_at is not None
    assert completed.output["report_type"] == "operational"
    assert "metrics" in completed.output
    assert "kpis" in completed.output


@pytest.mark.asyncio
async def test_start_transitions_queued_to_generating(repos):
    definitions = ReportDefinitionService(repos)
    runs = ReportRunService(repos)
    definition = await definitions.register_report(TENANT, name="Manual Step Report", report_type="custom")
    run = await runs.request_run(TENANT, definition.id)

    started = await runs.start(TENANT, run.id)
    assert started.status == "generating"


@pytest.mark.asyncio
async def test_list_for_definition_returns_runs_newest_first(repos):
    definitions = ReportDefinitionService(repos)
    runs = ReportRunService(repos)
    definition = await definitions.register_report(TENANT, name="Compliance Digest", report_type="compliance")

    first = await runs.request_run(TENANT, definition.id)
    await runs.generate(TENANT, first.id)
    second = await runs.request_run(TENANT, definition.id)
    await runs.generate(TENANT, second.id)

    history = await runs.list_for_definition(TENANT, definition.id)
    assert len(history) == 2
    assert history[0].id == second.id


@pytest.mark.asyncio
async def test_explicit_fail_requires_a_generating_run(repos):
    definitions = ReportDefinitionService(repos)
    runs = ReportRunService(repos)
    definition = await definitions.register_report(TENANT, name="Failing Report", report_type="custom")
    run = await runs.request_run(TENANT, definition.id)

    # a queued run can't be failed directly -- it has to be picked up (start()) first,
    # the same guarded transition graph every other AIOS platform's job-style entities use.
    with pytest.raises(ReportGenerationFailedError):
        await runs.fail(TENANT, run.id, error="too early")

    await runs.start(TENANT, run.id)
    failed = await runs.fail(TENANT, run.id, error="upstream data source unavailable")
    assert failed.status == "failed"
    assert failed.error == "upstream data source unavailable"


@pytest.mark.asyncio
async def test_fail_after_completion_raises(repos):
    definitions = ReportDefinitionService(repos)
    runs = ReportRunService(repos)
    definition = await definitions.register_report(TENANT, name="Already Done Report", report_type="custom")
    run = await runs.request_run(TENANT, definition.id)
    completed = await runs.generate(TENANT, run.id)

    with pytest.raises(ReportGenerationFailedError):
        await runs.fail(TENANT, completed.id, error="too late")
