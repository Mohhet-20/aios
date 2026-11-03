"""Environment Management: the 8 declared environment types
(development, testing, QA, staging, production, sandbox, customer
preview, enterprise dedicated) a deployment or rollout can target.

`register_environment` is a get-or-create upsert keyed on
(tenant_id, name) behind a commit-spanning `asyncio.Lock` — the same
pattern established across every prior AIOS platform for check-then-
act races that span multiple statements (separate callers own
separate DB connections; SQLite only makes a write visible to others
once committed, and the lock must be held until that commit happens,
not just until the row is flushed, or a waiting caller can still
observe pre-commit state). This is release_platform's one identified
lock candidate — every other get-or-create-shaped write in this
platform (feature flag overrides, license seat counters) either
tolerates last-write-wins or is idempotent by construction, as
documented in their own modules."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from release_platform.config.settings import get_settings
from release_platform.core.exceptions import EnvironmentNotFoundError, UnsupportedEnvironmentTypeError
from release_platform.models.environment import EnvironmentModel
from release_platform.repositories.registry import RepositoryRegistry


class EnvironmentService:
    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, environment_id: str) -> EnvironmentModel:
        env = await self.repos.environments.get_or_404(environment_id)
        if env.tenant_id != tenant_id:
            raise EnvironmentNotFoundError(f"Environment '{environment_id}' not found for tenant '{tenant_id}'")
        return env

    async def register_environment(
        self, tenant_id: str, *, name: str, environment_type: str, region: str | None = None
    ) -> EnvironmentModel:
        if environment_type not in self.settings.environment_types:
            raise UnsupportedEnvironmentTypeError(f"Unsupported environment type '{environment_type}'")
        lock_key = f"{tenant_id}:{name}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.environments.get_by_name(tenant_id, name)
            if existing is not None:
                return existing
            env = EnvironmentModel(tenant_id=tenant_id, name=name, environment_type=environment_type, region=region)
            env = await self.repos.environments.add(env)
            await self.repos.session.commit()
            return env

    async def deactivate(self, tenant_id: str, environment_id: str) -> EnvironmentModel:
        env = await self.get_or_404(tenant_id, environment_id)
        env.is_active = False
        return env

    async def activate(self, tenant_id: str, environment_id: str) -> EnvironmentModel:
        env = await self.get_or_404(tenant_id, environment_id)
        env.is_active = True
        return env

    async def list_environments(self, tenant_id: str, *, environment_type: str | None = None) -> list[EnvironmentModel]:
        return await self.repos.environments.list_for_tenant(tenant_id, environment_type=environment_type)
