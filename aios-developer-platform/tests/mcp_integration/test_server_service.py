import uuid

import pytest

from developer_platform.core.exceptions import McpError
from developer_platform.mcp_integration.server_service import McpServerService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_register_server_is_idempotent(repos, db_session):
    tenant_id = _tid()
    service = McpServerService(repos)
    first = await service.register_server(tenant_id, name="filesystem-mcp", endpoint_ref="stdio://fs-server")
    await db_session.commit()
    second = await service.register_server(tenant_id, name="filesystem-mcp", endpoint_ref="stdio://fs-server")
    await db_session.commit()
    assert first.id == second.id
    assert first.status == "registered"


async def test_register_unsupported_protocol_version_raises(repos, db_session):
    service = McpServerService(repos)
    with pytest.raises(McpError):
        await service.register_server(_tid(), name="x", endpoint_ref="stdio://x", protocol_version="0000-00-00")


async def test_connect_disconnect_lifecycle(repos, db_session):
    tenant_id = _tid()
    service = McpServerService(repos)
    server = await service.register_server(tenant_id, name="db-mcp", endpoint_ref="http://mcp.local")
    await db_session.commit()

    connected = await service.connect(tenant_id, server.id)
    await db_session.commit()
    assert connected.status == "connected"

    disconnected = await service.disconnect(tenant_id, server.id)
    await db_session.commit()
    assert disconnected.status == "disconnected"

    reconnected = await service.connect(tenant_id, server.id)
    await db_session.commit()
    assert reconnected.status == "connected"


async def test_mark_error_then_recover(repos, db_session):
    tenant_id = _tid()
    service = McpServerService(repos)
    server = await service.register_server(tenant_id, name="flaky-mcp", endpoint_ref="sse://flaky")
    await db_session.commit()
    await service.connect(tenant_id, server.id)
    await db_session.commit()

    errored = await service.mark_error(tenant_id, server.id)
    await db_session.commit()
    assert errored.status == "error"

    recovered = await service.connect(tenant_id, server.id)
    await db_session.commit()
    assert recovered.status == "connected"


async def test_invalid_transition_raises(repos, db_session):
    tenant_id = _tid()
    service = McpServerService(repos)
    server = await service.register_server(tenant_id, name="new-mcp", endpoint_ref="stdio://new")
    await db_session.commit()

    with pytest.raises(McpError):
        await service.disconnect(tenant_id, server.id)  # registered -> disconnected is not allowed


async def test_operations_scoped_to_tenant(repos, db_session):
    tenant_a = _tid()
    tenant_b = _tid()
    service = McpServerService(repos)
    server = await service.register_server(tenant_a, name="scoped-mcp", endpoint_ref="stdio://scoped")
    await db_session.commit()

    with pytest.raises(McpError):
        await service.connect(tenant_b, server.id)
