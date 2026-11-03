import pytest

from quality_platform.ai_quality.baseline_service import BaselineService
from quality_platform.ai_quality.evaluation_service import EvaluationService
from quality_platform.ai_quality.regression_scan_service import RegressionScanService
from quality_platform.core.exceptions import (
    InvalidTransitionError,
    RegressionDetectedError,
    UnsupportedAiQualityDimensionError,
)
from quality_platform.domain.enums import RegressionSeverity

pytestmark = pytest.mark.asyncio


async def test_set_baseline_creates_then_upserts(repos):
    # A commit-spanning-lock method durably commits (bypassing this
    # fixture's rollback teardown), so this must use a subject_ref no
    # other test's exact-count/exact-id assertion depends on staying
    # isolated -- in particular, distinct from the generic "agent:1"
    # the repository schema smoke test uses for the same tenant and
    # dimension.
    svc = BaselineService(repos)
    created = await svc.set_baseline("t1", "groundedness", "agent:upsert-probe", baseline_score=90.0, sample_size=10)
    updated = await svc.set_baseline("t1", "groundedness", "agent:upsert-probe", baseline_score=92.0, sample_size=20)
    assert updated.id == created.id
    assert updated.baseline_score == 92.0
    assert updated.sample_size == 20


async def test_set_baseline_rejects_unsupported_dimension(repos):
    svc = BaselineService(repos)
    with pytest.raises(UnsupportedAiQualityDimensionError):
        await svc.set_baseline("t1", "not-a-dimension", "agent:upsert-probe-invalid", baseline_score=90.0, sample_size=1)


async def test_run_scan_fails_without_baseline(repos):
    scans = RegressionScanService(repos)
    scan = await scans.request_scan("t1", "groundedness", "agent:no-baseline")
    finished = await scans.run_scan("t1", scan.id)
    assert finished.status == "failed"
    assert "baseline" in finished.error.lower()


async def test_run_scan_fails_without_evaluations(repos):
    baselines = BaselineService(repos)
    scans = RegressionScanService(repos)
    await baselines.set_baseline("t1", "groundedness", "agent:no-eval", baseline_score=90.0, sample_size=10)
    scan = await scans.request_scan("t1", "groundedness", "agent:no-eval")
    finished = await scans.run_scan("t1", scan.id)
    assert finished.status == "failed"
    assert "evaluation" in finished.error.lower()


async def test_run_scan_detects_critical_regression(repos):
    baselines = BaselineService(repos)
    evaluations = EvaluationService(repos)
    scans = RegressionScanService(repos)

    await baselines.set_baseline("t1", "groundedness", "agent:regressed", baseline_score=100.0, sample_size=10)
    await evaluations.record_evaluation("t1", "groundedness", "agent:regressed", score=80.0)  # -20%

    scan = await scans.request_scan("t1", "groundedness", "agent:regressed")
    finished = await scans.run_scan("t1", scan.id)

    assert finished.status == "completed"
    assert finished.severity == RegressionSeverity.CRITICAL.value
    assert finished.delta_pct == -20.0

    with pytest.raises(RegressionDetectedError):
        scans.assert_no_regression(finished)


async def test_run_scan_no_regression_on_improvement(repos):
    baselines = BaselineService(repos)
    evaluations = EvaluationService(repos)
    scans = RegressionScanService(repos)

    await baselines.set_baseline("t1", "groundedness", "agent:improved", baseline_score=80.0, sample_size=10)
    await evaluations.record_evaluation("t1", "groundedness", "agent:improved", score=90.0)

    scan = await scans.request_scan("t1", "groundedness", "agent:improved")
    finished = await scans.run_scan("t1", scan.id)

    assert finished.status == "completed"
    assert finished.severity == RegressionSeverity.NONE.value
    scans.assert_no_regression(finished)  # should not raise


async def test_cannot_complete_scan_without_start(repos):
    scans = RegressionScanService(repos)
    scan = await scans.request_scan("t1", "groundedness", "agent:direct")
    from quality_platform.domain.enums import RegressionSeverity as RS
    with pytest.raises(InvalidTransitionError):
        await scans.complete(
            "t1", scan.id, baseline_score=1.0, current_score=1.0, delta_pct=0.0, severity=RS.NONE, result={}
        )
