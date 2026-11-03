"""PolicyEngine: the enforcement point for rate limiting and resource
quotas — the parts of Safety & Governance that gate an action *before* it
happens rather than recording it after. RBAC (permissions/rbac_service.py)
answers "is this principal allowed to act on this resource at all";
PolicyEngine answers "even if allowed, has this principal/agent hit a
guardrail right now."
"""
from __future__ import annotations

from datetime import timedelta

from agent_platform.config.settings import Settings
from agent_platform.core.exceptions import ResourceQuotaExceededError
from agent_platform.models.agent import AgentModel
from agent_platform.models.task import TaskModel
from agent_platform.repositories.registry import RepositoryRegistry
from agent_platform.clock import utc_now


class PolicyEngine:
    def __init__(self, repos: RepositoryRegistry, settings: Settings):
        self.repos = repos
        self.settings = settings

    async def check_rate_limit(self, principal_id: str) -> None:
        since = utc_now() - timedelta(minutes=1)
        count = await self.repos.executions.count_recent_by_triggerer(principal_id, since=since)
        if count >= self.settings.rate_limit_tasks_per_minute:
            raise ResourceQuotaExceededError(
                f"principal '{principal_id}' has issued {count} task executions in the last minute "
                f"(limit={self.settings.rate_limit_tasks_per_minute}/min)"
            )

    async def check_resource_quota(self, agent: AgentModel) -> None:
        limits = agent.resource_limits or {}
        max_concurrent = limits.get("max_concurrent_tasks")
        if max_concurrent is not None:
            running = await self.repos.executions.count_running_for_agent(agent.id)
            if running >= max_concurrent:
                raise ResourceQuotaExceededError(
                    f"agent '{agent.id}' already has {running} running execution(s), at its "
                    f"max_concurrent_tasks limit of {max_concurrent}"
                )

    def requires_approval(self, agent: AgentModel, task: TaskModel) -> bool:
        """An agent explicitly marked non-autonomous always needs a human
        in the loop (that's what `is_autonomous=False` means); a task can
        also be flagged sensitive in its own context regardless of the
        agent, e.g. by the planner or a human operator."""
        if not agent.is_autonomous:
            return True
        return bool((task.context or {}).get("sensitive"))
