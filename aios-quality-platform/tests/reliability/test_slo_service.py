import pytest

from quality_platform.core.exceptions import UnsupportedReliabilityMetricError, ValidationError
from quality_platform.reliability.reliability_snapshot_service import ReliabilitySnapshotService
from quality_platform.reliability.slo_service import SloService

pytestmark = pytest.mark.asyncio


async def test_register_slo_creates_with_defaults(repos):
    svc = SloService(repos)
    slo = await svc.register_slo("t1", name="checkout-availability", service_ref="svc:checkout")
    assert slo.target_pct == svc.settings.reliability_default_slo_target
    assert slo.window_days == svc.settings.reliability_error_budget_window_days
    assert slo.status == "meeting"


async def test_register_slo_is_idempotent_by_name(repos):
    svc = SloService(repos)
    first = await svc.register_slo("t1", name="checkout-availability-2", service_ref="svc:checkout")
    second = await svc.register_slo("t1", name="checkout-availability-2", service_ref="svc:checkout")
    assert first.id == second.id


async def test_record_snapshot_rejects_unsupported_metric(repos):
    snapshots = ReliabilitySnapshotService(repos)
    with pytest.raises(UnsupportedReliabilityMetricError):
        await snapshots.record_snapshot("t1", "svc:checkout", metric_type="not-a-metric", value=1.0)


async def test_evaluate_slo_breached_from_snapshot(repos):
    svc = SloService(repos)
    snapshots = ReliabilitySnapshotService(repos)
    slo = await svc.register_slo("t1", name="checkout-availability-3", service_ref="svc:checkout-3", target_pct=99.9)
    await snapshots.record_snapshot("t1", "svc:checkout-3", metric_type="availability", value=99.5)
    evaluated = await svc.evaluate_slo("t1", slo.id)
    assert evaluated.status == "breached"


async def test_evaluate_slo_meeting_with_explicit_current(repos):
    svc = SloService(repos)
    slo = await svc.register_slo("t1", name="checkout-availability-4", service_ref="svc:checkout-4", target_pct=99.0)
    evaluated = await svc.evaluate_slo("t1", slo.id, current_pct=99.99)
    assert evaluated.status == "meeting"


async def test_evaluate_slo_without_snapshot_raises(repos):
    svc = SloService(repos)
    slo = await svc.register_slo("t1", name="checkout-availability-5", service_ref="svc:checkout-5")
    with pytest.raises(ValidationError):
        await svc.evaluate_slo("t1", slo.id)
