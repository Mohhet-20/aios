from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from perf_platform.models.cache import CacheEntryModel, CacheStatModel
from perf_platform.models.cost import BudgetModel, CostAlertModel, CostRecordModel
from perf_platform.models.observability import BenchmarkRunModel, LatencySampleModel, ThroughputSampleModel
from perf_platform.models.optimization import RecommendationModel
from perf_platform.models.routing import RoutingDecisionModel, RoutingPolicyModel
from perf_platform.models.scalability import GpuPoolModel

TENANT = "t1"


@pytest.mark.asyncio
async def test_cache_entry_roundtrip(repos):
    entry = await repos.cache_entries.add(CacheEntryModel(tenant_id=TENANT, layer="memory", key="k1", value="v1"))
    await repos.session.commit()
    fetched = await repos.cache_entries.get_by_key(TENANT, "memory", "k1")
    assert fetched is not None
    assert fetched.id == entry.id


@pytest.mark.asyncio
async def test_cache_entry_get_many(repos):
    a = await repos.cache_entries.add(CacheEntryModel(tenant_id=TENANT, layer="memory", key="a", value="1"))
    b = await repos.cache_entries.add(CacheEntryModel(tenant_id=TENANT, layer="memory", key="b", value="2"))
    await repos.session.commit()
    many = await repos.cache_entries.get_many([a.id, b.id, "missing-id"])
    assert [m.id for m in many] == [a.id, b.id]


@pytest.mark.asyncio
async def test_cache_entry_list_expired(repos):
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    await repos.cache_entries.add(CacheEntryModel(tenant_id=TENANT, layer="disk", key="exp", value="v", ttl_expires_at=past))
    await repos.session.commit()
    expired = await repos.cache_entries.list_expired(TENANT)
    assert any(e.key == "exp" for e in expired)


@pytest.mark.asyncio
async def test_cache_stat_roundtrip(repos):
    await repos.cache_stats.add(CacheStatModel(tenant_id=TENANT, layer="memory", hits=10, misses=2))
    await repos.session.commit()
    stat = await repos.cache_stats.get_for_layer(TENANT, "memory")
    assert stat is not None and stat.hits == 10


@pytest.mark.asyncio
async def test_routing_policy_and_decision(repos):
    await repos.routing_policies.add(
        RoutingPolicyModel(tenant_id=TENANT, scope_type="organization", scope_id="org-1", allowed_tiers=["small", "medium"])
    )
    await repos.session.commit()
    policy = await repos.routing_policies.get_for_scope(TENANT, "organization", "org-1")
    assert policy is not None

    await repos.routing_decisions.add(
        RoutingDecisionModel(tenant_id=TENANT, task_complexity="simple", chosen_tier="small", user_tier="free", estimated_cost_usd=0.001, reasoning="r")
    )
    await repos.session.commit()
    decisions = await repos.routing_decisions.list_for_tenant(TENANT)
    assert len(decisions) == 1


@pytest.mark.asyncio
async def test_cost_record_and_budget(repos):
    now = datetime.now(timezone.utc)
    await repos.cost_records.add(CostRecordModel(tenant_id=TENANT, category="token", entity_type="user", entity_id="u-1", amount_usd=1.5, recorded_at=now))
    await repos.cost_records.add(CostRecordModel(tenant_id=TENANT, category="token", entity_type="user", entity_id="u-1", amount_usd=2.5, recorded_at=now))
    await repos.session.commit()
    total = await repos.cost_records.total_for_entity(TENANT, "user", "u-1")
    assert total == 4.0

    budget = await repos.budgets.add(BudgetModel(tenant_id=TENANT, entity_type="user", entity_id="u-1", limit_usd=100.0))
    await repos.session.commit()
    fetched = await repos.budgets.get_for_entity(TENANT, "user", "u-1")
    assert fetched is not None and fetched.id == budget.id

    await repos.cost_alerts.add(CostAlertModel(tenant_id=TENANT, budget_id=budget.id, threshold_pct=80.0, spend_usd=80.0, message="80% of budget used"))
    await repos.session.commit()
    alerts = await repos.cost_alerts.list_for_budget(TENANT, budget.id)
    assert len(alerts) == 1


@pytest.mark.asyncio
async def test_recommendation_roundtrip(repos):
    await repos.recommendations.add(RecommendationModel(tenant_id=TENANT, category="caching", title="Cache hot endpoint", estimated_savings_usd=50.0))
    await repos.session.commit()
    recs = await repos.recommendations.list_for_tenant(TENANT)
    assert len(recs) == 1


@pytest.mark.asyncio
async def test_observability_roundtrip(repos):
    now = datetime.now(timezone.utc)
    await repos.latency_samples.add(LatencySampleModel(tenant_id=TENANT, operation="GET /x", duration_ms=120.0, recorded_at=now))
    await repos.throughput_samples.add(ThroughputSampleModel(tenant_id=TENANT, operation="GET /x", request_count=500, window_seconds=60.0, recorded_at=now))
    await repos.benchmark_runs.add(BenchmarkRunModel(tenant_id=TENANT, name="cache-speedup"))
    await repos.session.commit()
    assert len(await repos.latency_samples.list_for_operation(TENANT, "GET /x")) == 1
    assert len(await repos.throughput_samples.list_for_operation(TENANT, "GET /x")) == 1
    assert len(await repos.benchmark_runs.list_for_tenant(TENANT)) == 1


@pytest.mark.asyncio
async def test_gpu_pool_roundtrip(repos):
    await repos.gpu_pools.add(GpuPoolModel(tenant_id=TENANT, name="shared-a100", pool_type="shared", gpu_count=8))
    await repos.session.commit()
    pool = await repos.gpu_pools.get_by_name(TENANT, "shared-a100")
    assert pool is not None
    pools = await repos.gpu_pools.list_for_tenant(TENANT)
    assert len(pools) == 1
