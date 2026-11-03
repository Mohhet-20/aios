"""Auto-optimization recommendation engine: mines the signals every
other module in this platform already records (cache stats, latency
samples, routing decisions, budget utilization) and turns them into
actionable, deduplicated `RecommendationModel` rows with a guarded
editorial lifecycle (see domain/entities.py`Recommendation`)."""
from __future__ import annotations

from perf_platform.config.settings import get_settings
from perf_platform.core.exceptions import RecommendationNotFoundError
from perf_platform.cost_intelligence.cost_service import BudgetService
from perf_platform.cost_intelligence.pricing_rules import token_cost_usd
from perf_platform.domain.entities import Recommendation
from perf_platform.domain.enums import RecommendationStatus
from perf_platform.models.optimization import RecommendationModel
from perf_platform.observability.metrics_rules import percentile
from perf_platform.optimization.recommendation_rules import (
    budget_near_exhaustion_recommendation,
    high_latency_recommendation,
    low_cache_hit_rate_recommendation,
    model_tier_overprovisioning_recommendation,
)
from perf_platform.repositories.registry import RepositoryRegistry


class RecommendationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, recommendation_id: str) -> RecommendationModel:
        rec = await self.repos.recommendations.get_or_404(recommendation_id)
        if rec.tenant_id != tenant_id:
            raise RecommendationNotFoundError(f"Recommendation '{recommendation_id}' not found for tenant '{tenant_id}'")
        return rec

    async def _upsert(self, tenant_id: str, candidate: dict) -> RecommendationModel:
        """Dedupe on (category, target_ref) among still-open
        (proposed/accepted) recommendations — re-running generation
        shouldn't spam duplicate rows for a condition that's still
        true."""
        existing = [
            r for r in await self.repos.recommendations.list_for_tenant(tenant_id, category=candidate["category"])
            if r.target_ref == candidate.get("target_ref") and r.status in {RecommendationStatus.PROPOSED.value, RecommendationStatus.ACCEPTED.value}
        ]
        if existing:
            return existing[0]
        rec = await self.repos.recommendations.add(
            RecommendationModel(
                tenant_id=tenant_id, category=candidate["category"], title=candidate["title"],
                description=candidate["description"], target_ref=candidate.get("target_ref"),
                estimated_savings_usd=candidate.get("estimated_savings_usd", 0.0),
            )
        )
        await self.repos.session.commit()
        return rec

    async def generate_from_cache_stats(self, tenant_id: str) -> list[RecommendationModel]:
        stats = await self.repos.cache_stats.list_for_tenant(tenant_id)
        created = []
        for stat in stats:
            if stat.hits + stat.misses < 10:
                continue  # not enough samples to judge the hit rate yet
            candidate = low_cache_hit_rate_recommendation(
                layer=stat.layer, hit_rate_pct=stat.hit_rate_pct, threshold_pct=self.settings.low_cache_hit_rate_threshold_pct,
            )
            if candidate:
                created.append(await self._upsert(tenant_id, candidate))
        return created

    async def generate_from_latency(self, tenant_id: str, operation: str) -> RecommendationModel | None:
        samples = await self.repos.latency_samples.list_for_operation(tenant_id, operation)
        if len(samples) < 5:
            return None
        p99 = percentile([s.duration_ms for s in samples], 99.0)
        candidate = high_latency_recommendation(operation=operation, p99_ms=p99, threshold_ms=self.settings.high_latency_p99_ms_threshold)
        return await self._upsert(tenant_id, candidate) if candidate else None

    async def generate_from_routing_decisions(self, tenant_id: str) -> list[RecommendationModel]:
        decisions = await self.repos.routing_decisions.list_for_tenant(tenant_id, limit=500)
        groups: dict[tuple[str, str], list[float]] = {}
        for d in decisions:
            groups.setdefault((d.task_complexity, d.chosen_tier), []).append(d.estimated_cost_usd)

        created = []
        for (complexity, tier), costs in groups.items():
            avg_cost = sum(costs) / len(costs)
            baseline_cost = token_cost_usd(self.settings, model_tier="small", input_tokens=500, output_tokens=500)
            candidate = model_tier_overprovisioning_recommendation(
                task_complexity=complexity, chosen_tier=tier, occurrences=len(costs),
                cost_delta_usd_per_request=max(avg_cost - baseline_cost, 0.0),
            )
            if candidate:
                created.append(await self._upsert(tenant_id, candidate))
        return created

    async def generate_from_budget(self, tenant_id: str, *, entity_type: str, entity_id: str) -> RecommendationModel | None:
        budget_svc = BudgetService(self.repos)
        try:
            utilization = await budget_svc.utilization_pct(tenant_id, entity_type, entity_id)
        except Exception:
            return None
        candidate = budget_near_exhaustion_recommendation(entity_type=entity_type, entity_id=entity_id, utilization_pct=utilization)
        return await self._upsert(tenant_id, candidate) if candidate else None

    async def list_for_tenant(self, tenant_id: str, *, status: str | None = None, category: str | None = None) -> list[RecommendationModel]:
        return await self.repos.recommendations.list_for_tenant(tenant_id, status=status, category=category)

    async def _apply_transition(self, tenant_id: str, recommendation_id: str, transition_name: str) -> RecommendationModel:
        row = await self.get_or_404(tenant_id, recommendation_id)
        entity = Recommendation(id=row.id, status=RecommendationStatus(row.status))
        getattr(entity, transition_name)()
        row.status = entity.status.value
        return row

    async def accept(self, tenant_id: str, recommendation_id: str) -> RecommendationModel:
        return await self._apply_transition(tenant_id, recommendation_id, "accept")

    async def reject(self, tenant_id: str, recommendation_id: str) -> RecommendationModel:
        return await self._apply_transition(tenant_id, recommendation_id, "reject")

    async def apply(self, tenant_id: str, recommendation_id: str) -> RecommendationModel:
        return await self._apply_transition(tenant_id, recommendation_id, "apply")

    async def expire(self, tenant_id: str, recommendation_id: str) -> RecommendationModel:
        return await self._apply_transition(tenant_id, recommendation_id, "expire")
