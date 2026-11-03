"""Dynamic risk scoring for users, sessions, workflows, prompts,
agents, tools, data, and organizations. Risk scores are append-only
(see `models/risk.py`'s docstring) — there is no mutable "current
score" row. Instead, every new score starts from the *decayed* value
of the previous score (exponential half-life decay, so stale risk
fades rather than sticking around forever) plus the weighted
contribution of whatever just happened, clamped to [0, 100]."""
from __future__ import annotations

from security_platform.config.settings import Settings, get_settings
from security_platform.domain.entities import _aware, _now
from security_platform.domain.enums import RiskLevel
from security_platform.models.risk import RiskScoreModel
from security_platform.repositories.registry import RepositoryRegistry

_MEDIUM_THRESHOLD = 40.0


class RiskEngineService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _level_for_score(self, score: float) -> str:
        if score >= self.settings.risk_score_critical_threshold:
            return RiskLevel.CRITICAL.value
        if score >= self.settings.risk_score_high_threshold:
            return RiskLevel.HIGH.value
        if score >= _MEDIUM_THRESHOLD:
            return RiskLevel.MEDIUM.value
        return RiskLevel.LOW.value

    def _decayed_score(self, score: float, computed_at) -> float:
        half_life = self.settings.risk_score_decay_half_life_days
        if half_life <= 0:
            return score
        elapsed_days = (_now() - _aware(computed_at)).total_seconds() / 86400.0
        if elapsed_days <= 0:
            return score
        return max(0.0, score * (0.5 ** (elapsed_days / half_life)))

    async def current_score(self, tenant_id: str, entity_type: str, entity_id: str) -> float:
        """Decayed score derived from the latest persisted snapshot —
        never cached, so it can't silently go stale even between
        `record_score` calls."""
        latest = await self.repos.risk_scores.latest_for_entity(tenant_id, entity_type, entity_id)
        if latest is None:
            return 0.0
        return self._decayed_score(latest.score, latest.computed_at)

    async def record_score(
        self, tenant_id: str, entity_type: str, entity_id: str, factors: dict[str, float], *, base_on_current: bool = True
    ) -> RiskScoreModel:
        base = await self.current_score(tenant_id, entity_type, entity_id) if base_on_current else 0.0
        contribution = sum(factors.values())
        new_score = max(0.0, min(100.0, base + contribution))
        entry = RiskScoreModel(
            tenant_id=tenant_id, entity_type=entity_type, entity_id=entity_id, score=new_score,
            level=self._level_for_score(new_score), factors=dict(factors),
        )
        return await self.repos.risk_scores.add(entry)

    async def apply_event(self, tenant_id: str, entity_type: str, entity_id: str, event_name: str, weight: float) -> RiskScoreModel:
        """Convenience wrapper for the common case of a single named
        risk-contributing event (e.g. a failed login, a blocked
        guardrail violation, a DLP incident)."""
        return await self.record_score(tenant_id, entity_type, entity_id, {event_name: weight})

    async def refresh_decay(self, tenant_id: str, entity_type: str, entity_id: str) -> RiskScoreModel | None:
        """Persist a fresh snapshot reflecting only time-decay since
        the last score, no new factors — for periodic risk-review
        sweeps that want the audit trail to show risk fading even when
        nothing new has happened."""
        latest = await self.repos.risk_scores.latest_for_entity(tenant_id, entity_type, entity_id)
        if latest is None:
            return None
        return await self.record_score(tenant_id, entity_type, entity_id, {})

    async def top_risky(self, tenant_id: str, entity_type: str, *, limit: int = 20) -> list[RiskScoreModel]:
        return await self.repos.risk_scores.list_highest_current(tenant_id, entity_type, limit=limit)

    async def history(self, tenant_id: str, entity_type: str, entity_id: str, *, limit: int = 100) -> list[RiskScoreModel]:
        return await self.repos.risk_scores.history_for_entity(tenant_id, entity_type, entity_id, limit=limit)
