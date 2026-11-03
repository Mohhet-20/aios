import uuid

import pytest

from developer_platform.config.settings import Settings
from developer_platform.core.exceptions import McpPermissionDeniedError, McpSessionExpiredError, McpSessionNotFoundError
from developer_platform.mcp_integration.server_service import McpServerService
from developer_platform.mcp_integration.session_service import McpSessionService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def _server(repos, db_session, tenant_id):
    servers = McpServerService(repos)
    server = await servers.register_server(tenant_id, name="session-mcp", endpoint_ref="stdio://session")
    await db_session.commit()
    return server


async def test_start_and_touch_session(repos, db_session):
    tenant_id = _tid()
    server = await _server(repos, db_session, tenant_id)
    service = McpSessionService(repos)

    session = await service.start_session(tenant_id, mcp_server_id=server.id, client_id="client-1", permissions=["tools.invoke"])
    await db_session.commit()
    assert session.status == "active"

    touched = await service.touch_session(tenant_id, session.id)
    assert touched.last_activity_at is not None


async def test_check_permission_allows_declared_scope(repos, db_session):
    tenant_id = _tid()
    server = await _server(repos, db_session, tenant_id)
    service = McpSessionService(repos)
    session = await service.start_session(tenant_id, mcp_server_id=server.id, client_id="client-1", permissions=["resources.read"])
    await db_session.commit()

    await service.check_permission(tenant_id, session.id, "resources.read")


async def test_check_permission_denies_undeclared_scope(repos, db_session):
    tenant_id = _tid()
    server = await _server(repos, db_session, tenant_id)
    service = McpSessionService(repos)
    session = await service.start_session(tenant_id, mcp_server_id=server.id, client_id="client-1", permissions=["resources.read"])
    await db_session.commit()

    with pytest.raises(McpPermissionDeniedError):
        await service.check_permission(tenant_id, session.id, "tools.invoke")


async def test_wildcard_permission_allows_everything(repos, db_session):
    tenant_id = _tid()
    server = await _server(repos, db_session, tenant_id)
    service = McpSessionService(repos)
    session = await service.start_session(tenant_id, mcp_server_id=server.id, client_id="client-1", permissions=["*"])
    await db_session.commit()

    await service.check_permission(tenant_id, session.id, "anything.at.all")


async def test_expired_session_raises_and_transitions(repos, db_session):
    tenant_id = _tid()
    server = await _server(repos, db_session, tenant_id)
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, mcp_session_ttl_minutes=-1)
    service = McpSessionService(repos, settings=settings)
    session = await service.start_session(tenant_id, mcp_server_id=server.id, client_id="client-1")
    await db_session.commit()

    with pytest.raises(McpSessionExpiredError):
        await service.touch_session(tenant_id, session.id)
    await db_session.commit()

    active = await service.list_active(tenant_id)
    assert session.id not in [s.id for s in active]


async def test_close_session(repos, db_session):
    tenant_id = _tid()
    server = await _server(repos, db_session, tenant_id)
    service = McpSessionService(repos)
    session = await service.start_session(tenant_id, mcp_server_id=server.id, client_id="client-1")
    await db_session.commit()

    closed = await service.close_session(tenant_id, session.id)
    await db_session.commit()
    assert closed.status == "closed"

    with pytest.raises(McpSessionExpiredError):
        await service.touch_session(tenant_id, session.id)


async def test_unknown_session_raises_not_found(repos, db_session):
    service = McpSessionService(repos)
    with pytest.raises(McpSessionNotFoundError):
        await service.touch_session(_tid(), "not-a-real-id")
