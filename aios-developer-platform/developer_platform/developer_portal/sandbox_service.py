"""Sandbox environment provisioning: a bounded-lifetime scratch space
a developer spins up from the Developer Portal to try the platform
without touching real resources. Enforces
`sandbox_max_concurrent_per_developer` at provision time (counting
anything still provisioning/running) and guards the
provisioning -> running -> expired -> terminated lifecycle through the
`SandboxEnvironment` domain entity."""
from __future__ import annotations

from datetime import timedelta

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import NotFoundError, SandboxLimitExceededError, SandboxNotFoundError
from developer_platform.database.base import utcnow
from developer_platform.developer_portal.mappers import apply_sandbox_domain_to_model, sandbox_to_domain
from developer_platform.domain.entities import _aware
from developer_platform.domain.enums import SandboxStatus
from developer_platform.models.portal import SandboxEnvironmentModel
from developer_platform.repositories.registry import RepositoryRegistry


class SandboxService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def provision(self, tenant_id: str, developer_id: str) -> SandboxEnvironmentModel:
        active = await self.repos.sandbox_environments.list_active_for_developer(tenant_id, developer_id)
        if len(active) >= self.settings.sandbox_max_concurrent_per_developer:
            raise SandboxLimitExceededError(
                f"developer '{developer_id}' already has {len(active)} active sandbox(es) "
                f"(limit {self.settings.sandbox_max_concurrent_per_developer})"
            )
        sandbox = SandboxEnvironmentModel(
            tenant_id=tenant_id, developer_id=developer_id, status=SandboxStatus.PROVISIONING.value,
            started_at=utcnow(), expires_at=utcnow() + timedelta(minutes=self.settings.sandbox_ttl_minutes),
        )
        return await self.repos.sandbox_environments.add(sandbox)

    async def mark_running(self, sandbox_id: str) -> SandboxEnvironmentModel:
        sandbox = await self._get_or_404(sandbox_id)
        entity = sandbox_to_domain(sandbox)
        entity.mark_running()
        apply_sandbox_domain_to_model(entity, sandbox)
        return await self.repos.sandbox_environments.update(sandbox)

    async def expire(self, sandbox_id: str) -> SandboxEnvironmentModel:
        sandbox = await self._get_or_404(sandbox_id)
        entity = sandbox_to_domain(sandbox)
        entity.expire()
        apply_sandbox_domain_to_model(entity, sandbox)
        return await self.repos.sandbox_environments.update(sandbox)

    async def terminate(self, sandbox_id: str) -> SandboxEnvironmentModel:
        sandbox = await self._get_or_404(sandbox_id)
        entity = sandbox_to_domain(sandbox)
        entity.terminate()
        apply_sandbox_domain_to_model(entity, sandbox)
        return await self.repos.sandbox_environments.update(sandbox)

    async def sweep_expirations(self, tenant_id: str, developer_id: str) -> list[SandboxEnvironmentModel]:
        expired: list[SandboxEnvironmentModel] = []
        for sandbox in await self.repos.sandbox_environments.list_active_for_developer(tenant_id, developer_id):
            if sandbox.status == SandboxStatus.RUNNING.value and _aware(sandbox.expires_at) < utcnow():
                entity = sandbox_to_domain(sandbox)
                entity.expire()
                apply_sandbox_domain_to_model(entity, sandbox)
                await self.repos.sandbox_environments.update(sandbox)
                expired.append(sandbox)
        return expired

    async def list_for_developer(self, tenant_id: str, developer_id: str) -> list[SandboxEnvironmentModel]:
        return await self.repos.sandbox_environments.list_for_developer(tenant_id, developer_id)

    async def _get_or_404(self, sandbox_id: str) -> SandboxEnvironmentModel:
        try:
            return await self.repos.sandbox_environments.get_or_404(sandbox_id)
        except NotFoundError as exc:
            raise SandboxNotFoundError(f"Sandbox '{sandbox_id}' not found") from exc
