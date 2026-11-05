"""Real concurrency stress test: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every other AIOS
services. This platform has exactly one commit-spanning-lock
check-then-act sequence: `DocSpaceService.register_space` (get-or-
create by tenant_id+key). This test proves the per-key `asyncio.Lock`
actually prevents the duplicate-row race a naive "check then write"
sequence would produce under real concurrency."""
from __future__ import annotations

import asyncio

import pytest

from docs_platform.database.session import session_scope
from docs_platform.documentation.doc_space_service import DocSpaceService
from docs_platform.repositories.registry import RepositoryRegistry

TENANT = "stress-tenant"


async def _register_space_once() -> str:
    space_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = DocSpaceService(repos)
        space = await service.register_space(TENANT, key="stress-space", name="Stress Space", doc_type="developer")
        space_id = space.id
    return space_id


@pytest.mark.asyncio
async def test_concurrent_register_space_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_space_once() for _ in range(n_callers)])

    # Every concurrent caller should have been serialized onto the SAME
    # space row (same id)...
    assert len(set(results)) == 1

    # ...and only one row should actually exist in the DB — a naive
    # unlocked get-or-create sequence would insert one row per caller
    # that ran its "does this exist" check before any writer committed.
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        spaces = await repos.doc_spaces.list_for_tenant(TENANT)
    assert sum(1 for s in spaces if s.key == "stress-space") == 1
