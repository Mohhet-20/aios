import pytest

from quality_platform.core.exceptions import ObservabilityError
from quality_platform.observability.trend_service import TrendService

pytestmark = pytest.mark.asyncio


async def test_record_snapshot_rejects_unsupported_metric(repos):
    svc = TrendService(repos)
    with pytest.raises(ObservabilityError):
        await svc.record_snapshot("t1", metric_type="not-a-metric", value=1.0)


async def test_record_and_list_trend_ascending(repos):
    svc = TrendService(repos)
    await svc.record_snapshot("t1", metric_type="quality", value=70.0)
    await svc.record_snapshot("t1", metric_type="quality", value=80.0)
    await svc.record_snapshot("t1", metric_type="quality", value=90.0)
    trend = await svc.list_trend("t1", "quality")
    assert [s.value for s in trend] == [70.0, 80.0, 90.0]


async def test_direction_for_improving_series(repos):
    svc = TrendService(repos)
    for v in [50.0, 55.0, 85.0, 95.0]:
        await svc.record_snapshot("t1", metric_type="coverage", value=v)
    assert await svc.direction_for("t1", "coverage") == "improving"


async def test_scoped_by_subject_ref(repos):
    svc = TrendService(repos)
    await svc.record_snapshot("t1", metric_type="failure", value=1.0, subject_ref="svc:a")
    await svc.record_snapshot("t1", metric_type="failure", value=99.0, subject_ref="svc:b")
    scoped = await svc.list_trend("t1", "failure", subject_ref="svc:a")
    assert len(scoped) == 1
    assert scoped[0].value == 1.0
