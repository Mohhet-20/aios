from __future__ import annotations

import pytest

from perf_platform.core.exceptions import UnsupportedGpuPoolTypeError
from perf_platform.scalability.gpu_service import GpuPoolService

TENANT = "t-gpu"


@pytest.mark.asyncio
async def test_register_pool_is_idempotent_by_name(repos):
    svc = GpuPoolService(repos)
    first = await svc.register_pool(TENANT, name="pool-a", pool_type="shared", gpu_count=4)
    second = await svc.register_pool(TENANT, name="pool-a", pool_type="shared", gpu_count=4)
    assert first.id == second.id


@pytest.mark.asyncio
async def test_register_pool_rejects_unsupported_type(repos):
    svc = GpuPoolService(repos)
    with pytest.raises(UnsupportedGpuPoolTypeError):
        await svc.register_pool(TENANT, name="pool-b", pool_type="quantum", gpu_count=1)


@pytest.mark.asyncio
async def test_report_utilization_clamped(repos):
    svc = GpuPoolService(repos)
    pool = await svc.register_pool(TENANT, name="pool-c", pool_type="dedicated", gpu_count=8)
    updated = await svc.report_utilization(TENANT, pool.id, 150.0)
    assert updated.utilization_pct == 100.0


@pytest.mark.asyncio
async def test_activate_deactivate(repos):
    svc = GpuPoolService(repos)
    pool = await svc.register_pool(TENANT, name="pool-d", pool_type="spot", gpu_count=2)
    deactivated = await svc.deactivate(TENANT, pool.id)
    assert deactivated.is_active is False
    reactivated = await svc.activate(TENANT, pool.id)
    assert reactivated.is_active is True


@pytest.mark.asyncio
async def test_underutilized_pools(repos):
    svc = GpuPoolService(repos)
    low = await svc.register_pool(TENANT, name="pool-low", pool_type="reserved", gpu_count=4)
    await svc.report_utilization(TENANT, low.id, 5.0)
    high = await svc.register_pool(TENANT, name="pool-high", pool_type="reserved", gpu_count=4)
    await svc.report_utilization(TENANT, high.id, 90.0)

    underutilized = await svc.underutilized_pools(TENANT, threshold_pct=20.0)
    names = {p.name for p in underutilized}
    assert "pool-low" in names
    assert "pool-high" not in names
