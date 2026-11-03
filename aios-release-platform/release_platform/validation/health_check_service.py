"""Deployment Validation: post-deploy health verification across the
10 declared targets (application, API, database, workflow, AI
services, agent services, memory services, security platform,
monitoring platform, analytics platform). `run_all_checks` accepts an
injectable `checker` callable, the same "honest gap" pattern used by
`automation.GenerationJobService.run_job` in the Documentation
Platform — when no real checker is wired in, every target is recorded
as `degraded` with a note explaining why, rather than falsely claiming
`passed`. `is_deployment_healthy` is the read-side judgment call: a
deployment is healthy only once every declared target has at least
one recorded `passed` check and none has a `failed` check."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from release_platform.config.settings import get_settings
from release_platform.core.exceptions import HealthCheckFailedError, ValidationError
from release_platform.models.validation import HealthCheckRunModel
from release_platform.repositories.registry import RepositoryRegistry

Checker = Callable[[str], Awaitable[tuple[str, dict]]]


class HealthCheckService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def record_check(
        self, tenant_id: str, *, deployment_id: str, target: str, status: str, details: dict | None = None
    ) -> HealthCheckRunModel:
        if target not in self.settings.health_check_targets:
            raise ValidationError(f"Unsupported health check target '{target}'")
        if status not in {"passed", "failed", "degraded"}:
            raise ValidationError(f"Unsupported health check status '{status}'")
        run = HealthCheckRunModel(tenant_id=tenant_id, deployment_id=deployment_id, target=target, status=status, details=details or {})
        return await self.repos.health_check_runs.add(run)

    async def run_all_checks(self, tenant_id: str, deployment_id: str, *, checker: Checker | None = None) -> list[HealthCheckRunModel]:
        runs = []
        for target in self.settings.health_check_targets:
            if checker is not None:
                status, details = await checker(target)
            else:
                status, details = "degraded", {"note": "no checker function supplied — health is unknown, treated conservatively"}
            runs.append(await self.record_check(tenant_id, deployment_id=deployment_id, target=target, status=status, details=details))
        return runs

    async def list_for_deployment(self, tenant_id: str, deployment_id: str) -> list[HealthCheckRunModel]:
        return await self.repos.health_check_runs.list_for_deployment(tenant_id, deployment_id)

    async def is_deployment_healthy(self, tenant_id: str, deployment_id: str) -> bool:
        runs = await self.list_for_deployment(tenant_id, deployment_id)
        if not runs:
            return False
        if any(r.status == "failed" for r in runs):
            return False
        passed_targets = {r.target for r in runs if r.status == "passed"}
        return passed_targets == set(self.settings.health_check_targets)

    async def assert_healthy(self, tenant_id: str, deployment_id: str) -> None:
        if not await self.is_deployment_healthy(tenant_id, deployment_id):
            raise HealthCheckFailedError(f"Deployment '{deployment_id}' is not fully healthy")
