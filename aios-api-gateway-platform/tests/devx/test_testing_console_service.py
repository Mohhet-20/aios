from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import TestConsoleRequestFailedError
from gateway_platform.devx.testing_console_service import TestingConsoleService

TENANT = "devx-console-tenant"


def _boom_sender(payload):
    raise RuntimeError("connection refused")


def _ok_sender(payload):
    return 201, {"created": True}


@pytest.mark.asyncio
async def test_execute_default_sender_echoes_payload(repos):
    service = TestingConsoleService(repos)
    record = await service.execute(TENANT, "route-1", request_payload={"a": 1})
    assert record.status_code == 200
    assert record.response_payload == {"echo": {"a": 1}}


@pytest.mark.asyncio
async def test_execute_with_custom_sender(repos):
    service = TestingConsoleService(repos)
    record = await service.execute(TENANT, "route-2", request_payload={"name": "x"}, sender=_ok_sender)
    assert record.status_code == 201
    assert record.response_payload == {"created": True}


@pytest.mark.asyncio
async def test_execute_raises_on_sender_failure(repos):
    service = TestingConsoleService(repos)
    with pytest.raises(TestConsoleRequestFailedError):
        await service.execute(TENANT, "route-3", request_payload={}, sender=_boom_sender)


@pytest.mark.asyncio
async def test_list_for_route(repos):
    service = TestingConsoleService(repos)
    await service.execute(TENANT, "route-4", request_payload={"x": 1}, sender=_ok_sender)
    await service.execute(TENANT, "route-4", request_payload={"x": 2}, sender=_ok_sender)
    records = await service.list_for_route(TENANT, "route-4")
    assert len(records) == 2
