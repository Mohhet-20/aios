from __future__ import annotations

from datetime import datetime, timezone

import pytest

from perf_platform.cost_intelligence.cost_service import BudgetService, CostRecordService
from perf_platform.domain.enums import RecommendationStatus
from perf_platform.models.cache import CacheStatModel
from perf_platform.models.observability import LatencySampleModel
from perf_platform.models.routing import RoutingDecisionModel
from perf_platform.optimization.optimization_service import RecommendationService



@pytest.mark.asyncio
async def test_generate_from_cache_stats_flags_low_hit_rate(repos):
    TENANT = "t-optimize-1"
    await repos.cache_stats.add(CacheStatModel(tenant_id=TENANT, layer="prompt", hits=2, misses=18, hit_rate_pct=10.0))
    await repos.session.commit()
    svc = RecommendationService(repos)
    created = await svc.generate_from_cache_stats(TENANT)
    assert len(created) == 1
    assert created[0].category == "caching"


@pytest.mark.asyncio
async def test_generate_from_cache_stats_dedupes_on_rerun(repos):
    TENANT = "t-optimize-2"
    await repos.cache_stats.add(CacheStatModel(tenant_id=TENANT, layer="feature", hits=1, misses=19, hit_rate_pct=5.0))
    await repos.session.commit()
    svc = RecommendationService(repos)
    first = await svc.generate_from_cache_stats(TENANT)
    second = await svc.generate_from_cache_stats(TENANT)
    assert len(first) == 1
    assert first[0].id == second[0].id  # same row reused, not duplicated


@pytest.mark.asyncio
async def test_generate_from_latency_flags_high_p99(repos):
    TENANT = "t-optimize-3"
    now = datetime.now(timezone.utc)
    for ms in [100, 200, 300, 5000, 6000, 7000, 8000, 9000, 9500, 9900]:
        await repos.latency_samples.add(LatencySampleModel(tenant_id=TENANT, operation="slow_op", duration_ms=ms, recorded_at=now))
    await repos.session.commit()
    svc = RecommendationService(repos)
    rec = await svc.generate_from_latency(TENANT, "slow_op")
    assert rec is not None
    assert rec.category == "workflow"


@pytest.mark.asyncio
async def test_generate_from_routing_decisions_flags_overprovisioning(repos):
    TENANT = "t-optimize-4"
    for _ in range(10):
        await repos.routing_decisions.add(
            RoutingDecisionModel(tenant_id=TENANT, task_complexity="trivial", chosen_tier="reasoning", user_tier="enterprise", estimated_cost_usd=0.5, reasoning="x")
        )
    await repos.session.commit()
    svc = RecommendationService(repos)
    created = await svc.generate_from_routing_decisions(TENANT)
    assert any(r.category == "model_downgrade" for r in created)


@pytest.mark.asyncio
async def test_generate_from_budget_flags_near_exhaustion(repos):
    TENANT = "t-optimize-5"
    await BudgetService(repos).set_budget(TENANT, entity_type="organization", entity_id="org-2", limit_usd=100.0)
    await CostRecordService(repos).record(TENANT, category="gpu", entity_type="organization", entity_id="org-2", amount_usd=95.0)
    svc = RecommendationService(repos)
    rec = await svc.generate_from_budget(TENANT, entity_type="organization", entity_id="org-2")
    assert rec is not None


@pytest.mark.asyncio
async def test_lifecycle_accept_apply(repos):
    TENANT = "t-optimize-6"
    await repos.cache_stats.add(CacheStatModel(tenant_id=TENANT, layer="model", hits=1, misses=19, hit_rate_pct=5.0))
    await repos.session.commit()
    svc = RecommendationService(repos)
    [rec] = await svc.generate_from_cache_stats(TENANT)
    assert rec.status == RecommendationStatus.PROPOSED.value

    accepted = await svc.accept(TENANT, rec.id)
    assert accepted.status == RecommendationStatus.ACCEPTED.value

    applied = await svc.apply(TENANT, rec.id)
    assert applied.status == RecommendationStatus.APPLIED.value


@pytest.mark.asyncio
async def test_lifecycle_reject_is_terminal(repos):
    TENANT = "t-optimize-7"
    await repos.cache_stats.add(CacheStatModel(tenant_id=TENANT, layer="workflow", hits=1, misses=19, hit_rate_pct=5.0))
    await repos.session.commit()
    svc = RecommendationService(repos)
    [rec] = await svc.generate_from_cache_stats(TENANT)
    rejected = await svc.reject(TENANT, rec.id)
    assert rejected.status == RecommendationStatus.REJECTED.value
    with pytest.raises(Exception):
        await svc.accept(TENANT, rec.id)
