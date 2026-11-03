"""The policy engine's actual resolution logic: given a scope + an
optional specific resource within that scope, find the single
effective policy that applies and return its decision (allow/deny/
flag), honoring inheritance and active exceptions.

Resolution order (most specific wins):
1. An ACTIVE policy declared at exactly the requested scope + resource
   (`scope_ref_id`) — e.g. a policy attached to this exact agent.
2. Failing that, the nearest ACTIVE ancestor-scope policy with
   `scope_ref_id=None` (a broad catch-all — e.g. an organization-wide
   default that applies until something narrower overrides it).
3. Among tied candidates at the same specificity, lower `priority`
   wins (priority is a precedence number, not an importance rating —
   0 beats 100), then the most recently created policy wins.
4. If no policy applies at all, the platform defaults to ALLOW —
   this engine is advisory infrastructure for callers who explicitly
   check it, not a default-deny firewall; a tenant that wants
   default-deny behavior creates an organization-wide DENY policy.
5. An active, unexpired `PolicyException` for the exact resource
   forces the decision to ALLOW regardless of the resolved policy's
   effect — an exception is a carve-out, not a suggestion."""
from __future__ import annotations

from dataclasses import dataclass

from security_platform.domain.enums import PolicyScope
from security_platform.models.policies import PolicyModel
from security_platform.policies.exception_service import PolicyExceptionService
from security_platform.repositories.registry import RepositoryRegistry


@dataclass
class PolicyDecision:
    effect: str
    policy_id: str | None
    policy_name: str | None
    reason: str
    exception_applied: bool = False


def _pick_best(candidates: list[PolicyModel]) -> PolicyModel:
    return sorted(candidates, key=lambda p: (p.priority, -p.created_at.timestamp()))[0]


class PolicyEvaluationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.exceptions = PolicyExceptionService(repos)

    async def resolve_effective_policy(
        self, tenant_id: str, scope: str, scope_ref_id: str | None = None
    ) -> PolicyModel | None:
        requested_rank = PolicyScope(scope).rank
        active = await self.repos.policies.list_active_for_tenant(tenant_id)

        exact = [p for p in active if p.scope == scope and p.scope_ref_id == scope_ref_id]
        if exact:
            return _pick_best(exact)

        broader = [p for p in active if PolicyScope(p.scope).rank < requested_rank and p.scope_ref_id is None]
        if not broader:
            return None
        closest_rank = max(PolicyScope(p.scope).rank for p in broader)
        candidates = [p for p in broader if PolicyScope(p.scope).rank == closest_rank]
        return _pick_best(candidates)

    async def evaluate(self, tenant_id: str, scope: str, scope_ref_id: str | None = None) -> PolicyDecision:
        policy = await self.resolve_effective_policy(tenant_id, scope, scope_ref_id=scope_ref_id)
        if policy is None:
            return PolicyDecision(effect="allow", policy_id=None, policy_name=None, reason="no applicable policy — default allow")

        if scope_ref_id and await self.exceptions.is_exception_active(tenant_id, policy.id, scope_ref_id):
            return PolicyDecision(
                effect="allow", policy_id=policy.id, policy_name=policy.name,
                reason="active policy exception overrides the resolved policy", exception_applied=True,
            )

        return PolicyDecision(effect=policy.effect, policy_id=policy.id, policy_name=policy.name, reason=f"matched policy '{policy.name}'")
