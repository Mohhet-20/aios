"""Real concurrency stress test: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every other AIOS
services. This platform has exactly one commit-spanning-lock
check-then-act sequence: `EnvironmentService.register_environment`
(get-or-create by tenant_id+name). This test proves the per-key
`asyncio.Lock` actually prevents the duplicate-row race a naive
"check then write" sequence would produce under real concurrency."""
from __future__ import annotations

import asyncio

import pytest

from release_platform.database.session import session_scope
from release_platform.environments.environment_service import EnvironmentService
from release_platform.repositories.registry import RepositoryRegistry

TENANT = "stress-tenant"


async def _register_environment_once() -> str:
    env_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = EnvironmentService(repos)
        env = await service.register_environment(
            TENANT, name="stress-prod", environment_type="production", region="us-east-1"
        )
        env_id = env.id
    return env_id


@pytest.mark.asyncio
async def test_concurrent_register_environment_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_environment_once() for _ in range(n_callers)])

    # Every concurrent caller should have been serialized onto the SAME
    # environment row (same id)...
    assert len(set(results)) == 1

    # ...and only one row should actually exist in the DB — a naive
    # unlocked get-or-create sequence would insert one row per caller
    # that ran its "does this exist" check before any writer committed.
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        envs = await repos.environments.list_for_tenant(TENANT)
    assert sum(1 for e in envs if e.name == "stress-prod") == 1
