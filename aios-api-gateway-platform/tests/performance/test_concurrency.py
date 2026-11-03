"""Real concurrency stress tests: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every prior AIOS
platform. This platform has three commit-spanning-lock check-then-act
sequences (see each service's module docstring):
`ConnectorService.register_connector` (get-or-create by connector
type), `ServiceRegistryService.register_service` (get-or-create by
service name), and `EventTopicService.register_topic` (get-or-create
by topic name). Each test below proves the per-key `asyncio.Lock`
actually prevents the race a naive "check then write" sequence would
produce under real concurrency."""
from __future__ import annotations

import asyncio

import pytest

from gateway_platform.database.session import session_scope
from gateway_platform.events.topic_service import EventTopicService
from gateway_platform.integrations.connector_service import ConnectorService
from gateway_platform.repositories.registry import RepositoryRegistry
from gateway_platform.service_mesh.registry_service import ServiceRegistryService

TENANT = "stress-tenant"


async def _register_connector_once() -> str:
    connector_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = ConnectorService(repos)
        connector = await service.register_connector(TENANT, connector_type="github", name="GitHub")
        connector_id = connector.id
    return connector_id


@pytest.mark.asyncio
async def test_concurrent_register_connector_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_connector_once() for _ in range(n_callers)])

    # Every concurrent caller should have been serialized onto the SAME
    # connector row (same id) rather than each creating its own — this
    # is exactly the bug an unlocked "check existing, then insert"
    # sequence would produce under real concurrency.
    assert len(set(results)) == 1

    connectors = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        connectors = await repos.connectors.list_for_tenant(TENANT)
    assert sum(1 for c in connectors if c.connector_type == "github") == 1


async def _register_service_once() -> str:
    service_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = ServiceRegistryService(repos)
        registration = await service.register_service(TENANT, name="stress-service")
        service_id = registration.id
    return service_id


@pytest.mark.asyncio
async def test_concurrent_register_service_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_service_once() for _ in range(n_callers)])
    assert len(set(results)) == 1

    services = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        services = await repos.services.list_for_tenant(TENANT)
    assert sum(1 for s in services if s.name == "stress-service") == 1


async def _register_topic_once() -> str:
    topic_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = EventTopicService(repos)
        topic = await service.register_topic(TENANT, name="stress-topic", category="system")
        topic_id = topic.id
    return topic_id


@pytest.mark.asyncio
async def test_concurrent_register_topic_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_topic_once() for _ in range(n_callers)])
    assert len(set(results)) == 1

    topics = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        topics = await repos.event_topics.list_for_tenant(TENANT)
    assert sum(1 for t in topics if t.name == "stress-topic") == 1
