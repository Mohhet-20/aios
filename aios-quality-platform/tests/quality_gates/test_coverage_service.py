import pytest

from quality_platform.core.exceptions import UnsupportedCoverageTypeError
from quality_platform.quality_gates.coverage_service import CoverageService

pytestmark = pytest.mark.asyncio


async def test_record_snapshot_rejects_unsupported_type(repos):
    svc = CoverageService(repos)
    with pytest.raises(UnsupportedCoverageTypeError):
        await svc.record_snapshot("t1", "repo:1", coverage_type="not-a-type", covered_pct=90.0)


async def test_meets_target_true_above_threshold(repos):
    svc = CoverageService(repos)
    await svc.record_snapshot("t1", "repo:2", coverage_type="code", covered_pct=95.0)
    assert await svc.meets_target("t1", "repo:2", "code") is True


async def test_meets_target_false_below_threshold(repos):
    svc = CoverageService(repos)
    await svc.record_snapshot("t1", "repo:3", coverage_type="code", covered_pct=40.0)
    assert await svc.meets_target("t1", "repo:3", "code") is False


async def test_meets_target_false_without_any_snapshot(repos):
    svc = CoverageService(repos)
    assert await svc.meets_target("t1", "repo:no-data", "code") is False
