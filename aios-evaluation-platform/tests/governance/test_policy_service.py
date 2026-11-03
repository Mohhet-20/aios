import pytest

from eval_platform.config import settings as settings_module
from eval_platform.core.exceptions import AuthorizationError, ConcurrencyLimitExceededError, RateLimitExceededError
from eval_platform.governance.policy_service import ensure_same_workspace
from eval_platform.models.run import EvaluationRunModel


def test_ensure_same_workspace_passes_when_equal():
    ensure_same_workspace("ws-1", "ws-1")  # should not raise


def test_ensure_same_workspace_raises_when_different():
    with pytest.raises(AuthorizationError):
        ensure_same_workspace("ws-1", "ws-2")


@pytest.mark.asyncio
async def test_enforce_concurrency_limit_raises_over_cap(policy_service, workspace, repos, monkeypatch):
    settings_module.get_settings.cache_clear()
    monkeypatch.setenv("WORKSPACE_MAX_CONCURRENT_RUNS", "2")
    settings_module.get_settings.cache_clear()
    try:
        for _ in range(2):
            await repos.evaluation_runs.add(EvaluationRunModel(
                evaluation_id="eval-1", evaluation_version_id="ver-1", workspace_id=workspace.id, status="running",
            ))
        with pytest.raises(ConcurrencyLimitExceededError):
            await policy_service.enforce_concurrency_limit(workspace.id)
    finally:
        settings_module.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_enforce_concurrency_limit_passes_under_cap(policy_service, workspace):
    await policy_service.enforce_concurrency_limit(workspace.id)  # should not raise, no runs yet


@pytest.mark.asyncio
async def test_enforce_rate_limit_raises_over_cap(policy_service, workspace, repos, monkeypatch):
    settings_module.get_settings.cache_clear()
    monkeypatch.setenv("RATE_LIMIT_CALLS_PER_MINUTE", "2")
    settings_module.get_settings.cache_clear()
    try:
        for _ in range(2):
            await repos.evaluation_runs.add(EvaluationRunModel(
                evaluation_id="eval-1", evaluation_version_id="ver-1", workspace_id=workspace.id,
                triggered_by="user-1", status="succeeded",
            ))
        with pytest.raises(RateLimitExceededError):
            await policy_service.enforce_rate_limit("user-1")
    finally:
        settings_module.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_enforce_rate_limit_passes_under_cap(policy_service):
    await policy_service.enforce_rate_limit("brand-new-user")  # should not raise
