"""Orchestration shell around the pure `select_tier` rules: look up an
optional org/workspace/user routing policy, apply the deterministic
selection logic, estimate the request's cost at the chosen tier, and
log the decision for the auto-optimization engine and analytics to
mine later."""
from __future__ import annotations

from perf_platform.config.settings import get_settings
from perf_platform.core.exceptions import UnsupportedTaskComplexityError
from perf_platform.cost_intelligence.pricing_rules import token_cost_usd
from perf_platform.models.routing import RoutingDecisionModel, RoutingPolicyModel
from perf_platform.repositories.registry import RepositoryRegistry
from perf_platform.routing.routing_rules import select_tier


class RoutingPolicyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def set_policy(
        self, tenant_id: str, *, scope_type: str, scope_id: str, allowed_tiers: list[str], default_tier: str = "medium",
        max_cost_per_request_usd: float | None = None,
    ) -> RoutingPolicyModel:
        existing = await self.repos.routing_policies.get_for_scope(tenant_id, scope_type, scope_id)
        if existing is not None:
            existing.allowed_tiers = allowed_tiers
            existing.default_tier = default_tier
            existing.max_cost_per_request_usd = max_cost_per_request_usd
            policy = existing
        else:
            policy = await self.repos.routing_policies.add(
                RoutingPolicyModel(
                    tenant_id=tenant_id, scope_type=scope_type, scope_id=scope_id, allowed_tiers=allowed_tiers,
                    default_tier=default_tier, max_cost_per_request_usd=max_cost_per_request_usd,
                )
            )
        await self.repos.session.commit()
        return policy


class ModelRoutingService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def route(
        self, tenant_id: str, *,
        task_complexity: str,
        user_tier: str = "enterprise",
        latency_budget_ms: float | None = None,
        requires_vision: bool = False,
        requires_code: bool = False,
        policy_scope_type: str | None = None,
        policy_scope_id: str | None = None,
        estimated_input_tokens: int = 500,
        estimated_output_tokens: int = 500,
    ) -> RoutingDecisionModel:
        if task_complexity not in self.settings.task_complexity_levels:
            raise UnsupportedTaskComplexityError(f"Unsupported task complexity '{task_complexity}'")

        allowed_tiers = None
        if policy_scope_type and policy_scope_id:
            policy = await self.repos.routing_policies.get_for_scope(tenant_id, policy_scope_type, policy_scope_id)
            if policy is not None:
                allowed_tiers = policy.allowed_tiers

        tier, reasoning = select_tier(
            task_complexity=task_complexity, user_tier=user_tier, latency_budget_ms=latency_budget_ms,
            requires_vision=requires_vision, requires_code=requires_code, allowed_tiers=allowed_tiers,
        )
        estimated_cost = token_cost_usd(
            self.settings, model_tier=tier, input_tokens=estimated_input_tokens, output_tokens=estimated_output_tokens,
        )
        decision = await self.repos.routing_decisions.add(
            RoutingDecisionModel(
                tenant_id=tenant_id, task_complexity=task_complexity, chosen_tier=tier, user_tier=user_tier,
                latency_budget_ms=latency_budget_ms, estimated_cost_usd=estimated_cost, reasoning=reasoning,
            )
        )
        await self.repos.session.commit()
        return decision

    async def recent_decisions(self, tenant_id: str, *, limit: int = 100) -> list[RoutingDecisionModel]:
        return await self.repos.routing_decisions.list_for_tenant(tenant_id, limit=limit)
