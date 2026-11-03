import pytest

from quality_platform.certification.certification_run_service import CertificationRunService
from quality_platform.core.exceptions import InvalidTransitionError

pytestmark = pytest.mark.asyncio


async def test_certify_approves_high_scores(repos):
    svc = CertificationRunService(repos)
    run = await svc.request_run("t1", release_ref="rel:1")
    finished = await svc.certify(
        "t1", run.id, quality_score=95.0, reliability_score=95.0, security_score=95.0, performance_score=95.0, ai_quality_score=95.0
    )
    assert finished.status == "completed"
    assert finished.decision == "approved"
    assert finished.overall_score == 95.0


async def test_certify_rejects_low_scores(repos):
    svc = CertificationRunService(repos)
    run = await svc.request_run("t1", release_ref="rel:2")
    finished = await svc.certify("t1", run.id, quality_score=30.0, security_score=30.0)
    assert finished.decision == "rejected"


async def test_certify_fails_run_when_no_scores_supplied(repos):
    svc = CertificationRunService(repos)
    run = await svc.request_run("t1", release_ref="rel:3")
    finished = await svc.certify("t1", run.id)
    assert finished.status == "failed"
    assert "no category scores" in finished.error.lower()


async def test_cannot_complete_without_start(repos):
    svc = CertificationRunService(repos)
    run = await svc.request_run("t1", release_ref="rel:4")
    with pytest.raises(InvalidTransitionError):
        await svc.complete(
            "t1", run.id, quality_score=1.0, reliability_score=None, security_score=None, performance_score=None,
            ai_quality_score=None, overall_score=1.0, decision="rejected", report={},
        )


async def test_list_for_release_orders_desc(repos):
    svc = CertificationRunService(repos)
    run1 = await svc.request_run("t1", release_ref="rel:5")
    await svc.certify("t1", run1.id, quality_score=90.0)
    run2 = await svc.request_run("t1", release_ref="rel:5")
    await svc.certify("t1", run2.id, quality_score=91.0)

    runs = await svc.list_for_release("t1", "rel:5")
    assert len(runs) == 2
    assert runs[0].id == run2.id  # most recent first
