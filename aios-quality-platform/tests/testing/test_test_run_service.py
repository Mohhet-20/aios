import pytest

from quality_platform.core.exceptions import InvalidTransitionError, ValidationError
from quality_platform.testing.test_run_service import TestRunService
from quality_platform.testing.test_suite_service import TestSuiteService

pytestmark = pytest.mark.asyncio


async def _make_suite(repos, name="run-suite"):
    return await TestSuiteService(repos).register_suite("t1", name=name, test_type="unit")


async def test_request_run_requires_active_suite(repos):
    suite = await _make_suite(repos, "inactive-suite")
    runs = TestRunService(repos)
    await TestSuiteService(repos).deactivate_suite("t1", suite.id)
    with pytest.raises(ValidationError):
        await runs.request_run("t1", suite.id)


async def test_start_complete_transitions(repos):
    suite = await _make_suite(repos, "lifecycle-suite")
    runs = TestRunService(repos)
    run = await runs.request_run("t1", suite.id)
    assert run.status == "queued"
    started = await runs.start("t1", run.id)
    assert started.status == "running"
    completed = await runs.complete("t1", run.id, summary={"passed": 1})
    assert completed.status == "completed"
    assert completed.completed_at is not None


async def test_cannot_complete_without_start(repos):
    suite = await _make_suite(repos, "no-start-suite")
    runs = TestRunService(repos)
    run = await runs.request_run("t1", suite.id)
    with pytest.raises(InvalidTransitionError):
        await runs.complete("t1", run.id, summary={})


async def test_record_result_and_finish_run_completes(repos):
    suite = await _make_suite(repos, "results-suite")
    suite_svc = TestSuiteService(repos)
    case = await suite_svc.add_case("t1", suite.id, name="case-a", test_type="unit")
    runs = TestRunService(repos)
    run = await runs.request_run("t1", suite.id)
    await runs.start("t1", run.id)
    await runs.record_result("t1", run.id, case.id, result="passed", duration_ms=12.5)
    finished = await runs.finish_run("t1", run.id)
    assert finished.status == "completed"
    assert finished.summary["passed"] == 1
    assert finished.summary["total"] == 1


async def test_record_result_error_fails_run(repos):
    suite = await _make_suite(repos, "error-suite")
    suite_svc = TestSuiteService(repos)
    case = await suite_svc.add_case("t1", suite.id, name="case-b", test_type="unit")
    runs = TestRunService(repos)
    run = await runs.request_run("t1", suite.id)
    await runs.start("t1", run.id)
    await runs.record_result("t1", run.id, case.id, result="error")
    finished = await runs.finish_run("t1", run.id)
    assert finished.status == "failed"


async def test_flaky_detection_reclassifies_result(repos):
    suite = await _make_suite(repos, "flaky-suite")
    suite_svc = TestSuiteService(repos)
    case = await suite_svc.add_case("t1", suite.id, name="flaky-case", test_type="unit")
    runs = TestRunService(repos)

    # Seed alternating pass/fail history directly under distinct runs
    # so the 4th result (crossing the default threshold of 3
    # transitions) gets reclassified as flaky.
    outcomes = ["passed", "failed", "passed", "failed"]
    last = None
    for outcome in outcomes:
        run = await runs.request_run("t1", suite.id)
        await runs.start("t1", run.id)
        last = await runs.record_result("t1", run.id, case.id, result=outcome)

    assert last.result == "flaky"


async def test_is_case_flaky_reads_recent_history(repos):
    """Exercises is_case_flaky() directly against seeded pass/fail
    history (bypassing record_result's own reclassification, which
    would otherwise overwrite later entries with "flaky" and mask the
    pattern this test wants to assert on)."""
    suite = await _make_suite(repos, "flaky-history-suite")
    suite_svc = TestSuiteService(repos)
    case = await suite_svc.add_case("t1", suite.id, name="flaky-history-case", test_type="unit")
    runs = TestRunService(repos)
    run = await runs.request_run("t1", suite.id)
    await runs.start("t1", run.id)

    from quality_platform.models.testing import TestCaseResultModel

    for outcome in ("passed", "failed", "passed", "failed"):
        await repos.test_case_results.add(
            TestCaseResultModel(tenant_id="t1", test_run_id=run.id, test_case_id=case.id, result=outcome)
        )
    await repos.session.commit()

    assert await runs.is_case_flaky("t1", case.id) is True
