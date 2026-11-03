"""EvaluationPolicyService: the governance gate a run-starting caller
checks before `EvaluationRunService.start_run`/`BenchmarkRunService.
start_run` — a per-workspace concurrent-run cap and a per-triggerer
rate limit, both enforced against real database counts (not an
in-memory counter that drifts across processes), reusing
`EvaluationRunRepository.count_active_for_workspace`/
`count_recent_by_triggerer` built in the repository layer.

`ensure_same_workspace` is the workspace/org isolation guard: any
service binding two resources together (an evaluation to a dataset, a
benchmark to a dataset) should call it so a workspace can never
accidentally reference another workspace's data."""
from __future__ import annotations

from datetime import timedelta

from eval_platform.config.settings import get_settings
from eval_platform.core.exceptions import AuthorizationError, ConcurrencyLimitExceededError, RateLimitExceededError
from eval_platform.repositories.registry import RepositoryRegistry
from eval_platform.clock import utc_now


def ensure_same_workspace(resource_a_workspace_id: str, resource_b_workspace_id: str, *, context: str = "resources") -> None:
    if resource_a_workspace_id != resource_b_workspace_id:
        raise AuthorizationError(f"{context} belong to different workspaces and cannot be linked")


class EvaluationPolicyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def enforce_concurrency_limit(self, workspace_id: str) -> None:
        settings = get_settings()
        active = await self.repos.evaluation_runs.count_active_for_workspace(workspace_id)
        if active >= settings.workspace_max_concurrent_runs:
            raise ConcurrencyLimitExceededError(
                f"workspace '{workspace_id}' already has {active} active evaluation runs "
                f"(limit: {settings.workspace_max_concurrent_runs})"
            )

    async def enforce_rate_limit(self, triggered_by: str) -> None:
        settings = get_settings()
        since = utc_now() - timedelta(minutes=1)
        recent = await self.repos.evaluation_runs.count_recent_by_triggerer(triggered_by, since=since)
        if recent >= settings.rate_limit_calls_per_minute:
            raise RateLimitExceededError(
                f"principal '{triggered_by}' has started {recent} evaluation runs in the last minute "
                f"(limit: {settings.rate_limit_calls_per_minute})"
            )
