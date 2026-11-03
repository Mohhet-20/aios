"""Tests for dynamic risk scoring: level thresholds, exponential
decay of stale scores, factor accumulation, and top-risky / history
queries."""
from __future__ import annotations

from datetime import timedelta

import pytest

from security_platform.config.settings import Settings
from security_platform.domain.entities import _now
from security_platform.domain.enums import RiskLevel
from security_platform.models.risk import RiskScoreModel
from security_platform.risk_engine.risk_service import RiskEngineService

TENANT = "tenant-risk"


@pytest.mark.asyncio
async def test_current_score_is_zero_with_no_history(repos):
    service = RiskEngineService(repos, settings=Settings())
    assert await service.current_score(TENANT, "user", "user-1") == 0.0


@pytest.mark.asyncio
async def test_record_score_accumulates_factors_and_sets_level(repos):
    service = RiskEngineService(repos, settings=Settings(risk_score_high_threshold=75.0, risk_score_critical_threshold=90.0))
    entry = await service.record_score(TENANT, "user", "user-1", {"failed_login": 20.0, "new_device": 10.0})
    assert entry.score == pytest.approx(30.0)
    assert entry.level == RiskLevel.LOW.value


@pytest.mark.asyncio
async def test_record_score_clamped_to_100(repos):
    service = RiskEngineService(repos, settings=Settings())
    entry = await service.record_score(TENANT, "user", "user-2", {"catastrophic": 500.0})
    assert entry.score == 100.0
    assert entry.level == RiskLevel.CRITICAL.value


@pytest.mark.asyncio
async def test_apply_event_adds_single_factor_on_top_of_current(repos):
    service = RiskEngineService(repos, settings=Settings())
    await service.apply_event(TENANT, "session", "sess-1", "impossible_travel", 30.0)
    second = await service.apply_event(TENANT, "session", "sess-1", "brute_force_attempt", 25.0)
    assert second.score == pytest.approx(55.0, abs=0.5)


@pytest.mark.asyncio
async def test_score_decays_toward_zero_over_half_life(repos):
    settings = Settings(risk_score_decay_half_life_days=14.0)
    past = _now() - timedelta(days=14)
    await repos.risk_scores.add(
        RiskScoreModel(tenant_id=TENANT, entity_type="user", entity_id="user-decay", score=100.0, level="critical", factors={}, computed_at=past)
    )
    service = RiskEngineService(repos, settings=settings)
    decayed = await service.current_score(TENANT, "user", "user-decay")
    assert decayed == pytest.approx(50.0, rel=0.02)


@pytest.mark.asyncio
async def test_refresh_decay_persists_new_snapshot_without_new_factors(repos):
    settings = Settings(risk_score_decay_half_life_days=14.0)
    past = _now() - timedelta(days=14)
    await repos.risk_scores.add(
        RiskScoreModel(tenant_id=TENANT, entity_type="agent", entity_id="agent-1", score=80.0, level="high", factors={"x": 80.0}, computed_at=past)
    )
    service = RiskEngineService(repos, settings=settings)
    refreshed = await service.refresh_decay(TENANT, "agent", "agent-1")
    assert refreshed.score == pytest.approx(40.0, rel=0.02)
    assert refreshed.factors == {}

    history = await service.history(TENANT, "agent", "agent-1")
    assert len(history) == 2


@pytest.mark.asyncio
async def test_refresh_decay_returns_none_when_no_history(repos):
    service = RiskEngineService(repos, settings=Settings())
    assert await service.refresh_decay(TENANT, "agent", "agent-none") is None


@pytest.mark.asyncio
async def test_top_risky_orders_by_current_score_descending(repos):
    service = RiskEngineService(repos, settings=Settings())
    await service.record_score(TENANT, "tool", "tool-low", {"minor": 10.0})
    await service.record_score(TENANT, "tool", "tool-high", {"major": 90.0})
    top = await service.top_risky(TENANT, "tool", limit=5)
    assert [t.entity_id for t in top] == ["tool-high", "tool-low"]
