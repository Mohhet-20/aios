"""PolicyEngine: the enforcement point for rate limiting, concurrency
quotas, and sensitive-tool approval-gating — the parts of Governance
that gate a call *before* it happens rather than recording it after
(that's AuditService's job) or answering "is this principal allowed to
act on this resource at all" (that's RBACService's job). Three separate
concerns, three separate services, composed by whatever calls them
(currently: the Execution Engine, optionally — see its constructor's
`policy_engine`/`approval_service` kwargs)."""
from __future__ import annotations

from datetime import timedelta

from tool_platform.config.settings import Settings
from tool_platform.core.exceptions import ConcurrencyLimitExceededError, RateLimitExceededError
from tool_platform.models.tool import ToolModel, ToolVersionModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.clock import utc_now

_SENSITIVE_LEVELS = {"high", "critical"}


class PolicyEngine:
    def __init__(self, repos: RepositoryRegistry, settings: Settings):
        self.repos = repos
        self.settings = settings

    async def check_rate_limit(self, principal_id: str) -> None:
        since = utc_now() - timedelta(minutes=1)
        count = await self.repos.executions.count_recent_by_triggerer(principal_id, since=since)
        if count >= self.settings.rate_limit_calls_per_minute:
            raise RateLimitExceededError(
                f"principal '{principal_id}' has issued {count} tool call(s) in the last minute "
                f"(limit={self.settings.rate_limit_calls_per_minute}/min)"
            )

    async def check_tool_concurrency_quota(self, tool: ToolModel) -> None:
        running = await self.repos.executions.count_active_for_tool(tool.id)
        if running >= self.settings.max_concurrent_tool_executions:
            raise ConcurrencyLimitExceededError(
                f"tool '{tool.id}' already has {running} active execution(s), at the platform's "
                f"max_concurrent_tool_executions limit of {self.settings.max_concurrent_tool_executions}"
            )

    async def check_workspace_concurrency_quota(self, workspace_id: str) -> None:
        running = await self.repos.executions.count_active_for_workspace(workspace_id)
        if running >= self.settings.workspace_max_concurrent_executions:
            raise ConcurrencyLimitExceededError(
                f"workspace '{workspace_id}' already has {running} active execution(s), at its "
                f"workspace_max_concurrent_executions limit of {self.settings.workspace_max_concurrent_executions}"
            )

    def requires_approval(self, tool_version: ToolVersionModel) -> bool:
        """HIGH/CRITICAL sensitivity tool versions always need a resolved,
        unconsumed `ApprovalGateModel` before the Execution Engine will
        dispatch them — see `ToolSensitivity`'s docstring for the design
        this fulfills."""
        return tool_version.sensitivity_level in _SENSITIVE_LEVELS
