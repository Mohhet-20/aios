import pytest

from quality_platform.core.exceptions import QualityGateError, QualityGateFailedError
from quality_platform.quality_gates.quality_gate_service import QualityGateService

pytestmark = pytest.mark.asyncio


async def test_create_gate_is_idempotent_by_release_and_name(repos):
    svc = QualityGateService(repos)
    first = await svc.create_gate("t1", name="release-gate", release_ref="rel:1")
    second = await svc.create_gate("t1", name="release-gate", release_ref="rel:1")
    assert first.id == second.id
    assert first.status == "pending"


async def test_record_check_rejects_unsupported_type(repos):
    svc = QualityGateService(repos)
    gate = await svc.create_gate("t1", name="release-gate-2", release_ref="rel:2")
    with pytest.raises(QualityGateError):
        await svc.record_check("t1", gate.id, check_type="not-a-check", passed=True)


async def test_evaluate_gate_passes_when_score_meets_min(repos):
    svc = QualityGateService(repos)
    gate = await svc.create_gate("t1", name="release-gate-3", release_ref="rel:3", min_score=70.0)
    await svc.record_check("t1", gate.id, check_type="test_coverage", passed=True)
    await svc.record_check("t1", gate.id, check_type="security", passed=True)
    await svc.record_check("t1", gate.id, check_type="performance", passed=True)
    await svc.record_check("t1", gate.id, check_type="reliability", passed=False)
    evaluated = await svc.evaluate_gate("t1", gate.id)  # 3/4 = 75% >= 70
    assert evaluated.status == "passed"
    assert evaluated.evaluated_at is not None
    svc.assert_gate_passed(evaluated)  # should not raise


async def test_evaluate_gate_fails_when_score_below_min(repos):
    svc = QualityGateService(repos)
    gate = await svc.create_gate("t1", name="release-gate-4", release_ref="rel:4", min_score=80.0)
    await svc.record_check("t1", gate.id, check_type="test_coverage", passed=True)
    await svc.record_check("t1", gate.id, check_type="security", passed=False)
    evaluated = await svc.evaluate_gate("t1", gate.id)  # 1/2 = 50% < 80
    assert evaluated.status == "failed"
    with pytest.raises(QualityGateFailedError):
        svc.assert_gate_passed(evaluated)


async def test_evaluate_gate_with_no_checks_fails_closed(repos):
    svc = QualityGateService(repos)
    gate = await svc.create_gate("t1", name="release-gate-5", release_ref="rel:5")
    evaluated = await svc.evaluate_gate("t1", gate.id)
    assert evaluated.status == "failed"


async def test_waive_gate(repos):
    svc = QualityGateService(repos)
    gate = await svc.create_gate("t1", name="release-gate-6", release_ref="rel:6")
    waived = await svc.waive_gate("t1", gate.id)
    assert waived.status == "waived"
    svc.assert_gate_passed(waived)  # waived counts as passed for downstream callers


async def test_list_gates_filters_by_release(repos):
    svc = QualityGateService(repos)
    await svc.create_gate("t1", name="release-gate-7a", release_ref="rel:7")
    await svc.create_gate("t1", name="release-gate-7b", release_ref="rel:8")
    rel7_gates = await svc.list_gates("t1", release_ref="rel:7")
    assert len(rel7_gates) == 1
