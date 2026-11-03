from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import (
    RouteAlreadyExistsError,
    RouteNotFoundError,
    UnsupportedProtocolError,
    UnsupportedVisibilityError,
)
from gateway_platform.gateway_core.route_service import RouteRegistrationService

TENANT = "gw-tenant"


@pytest.mark.asyncio
async def test_register_and_activate_route(repos):
    service = RouteRegistrationService(repos)
    route = await service.register_route(TENANT, path="/v1/orders", method="post", target_service="orders-svc")
    assert route.status == "draft"
    assert route.method == "POST"

    activated = await service.activate_route(TENANT, route.id)
    assert activated.status == "active"


@pytest.mark.asyncio
async def test_duplicate_route_rejected(repos):
    service = RouteRegistrationService(repos)
    await service.register_route(TENANT, path="/v1/dupe", method="GET", target_service="svc-a")
    with pytest.raises(RouteAlreadyExistsError):
        await service.register_route(TENANT, path="/v1/dupe", method="GET", target_service="svc-b")


@pytest.mark.asyncio
async def test_unsupported_protocol_and_visibility_rejected(repos):
    service = RouteRegistrationService(repos)
    with pytest.raises(UnsupportedProtocolError):
        await service.register_route(TENANT, path="/v1/x", target_service="svc", protocol="carrier-pigeon")
    with pytest.raises(UnsupportedVisibilityError):
        await service.register_route(TENANT, path="/v1/y", target_service="svc", visibility="nobody")


@pytest.mark.asyncio
async def test_deprecate_reactivate_retire_lifecycle(repos):
    service = RouteRegistrationService(repos)
    route = await service.register_route(TENANT, path="/v1/lifecycle", target_service="svc")
    await service.activate_route(TENANT, route.id)

    deprecated = await service.deprecate_route(TENANT, route.id)
    assert deprecated.status == "deprecated"

    reactivated = await service.reactivate_route(TENANT, route.id)
    assert reactivated.status == "active"

    await service.deprecate_route(TENANT, route.id)
    retired = await service.retire_route(TENANT, route.id)
    assert retired.status == "retired"


@pytest.mark.asyncio
async def test_match_route_excludes_retired(repos):
    service = RouteRegistrationService(repos)
    route = await service.register_route(TENANT, path="/v1/match", target_service="svc")
    await service.activate_route(TENANT, route.id)
    matched = await service.match_route(TENANT, "/v1/match", "GET")
    assert matched.id == route.id

    await service.deprecate_route(TENANT, route.id)
    await service.retire_route(TENANT, route.id)
    with pytest.raises(RouteNotFoundError):
        await service.match_route(TENANT, "/v1/match", "GET")


@pytest.mark.asyncio
async def test_list_routes_filters_by_status(repos):
    service = RouteRegistrationService(repos)
    r1 = await service.register_route(TENANT, path="/v1/list-a", target_service="svc")
    await service.register_route(TENANT, path="/v1/list-b", target_service="svc")
    await service.activate_route(TENANT, r1.id)

    active = await service.list_routes(TENANT, status="active")
    assert all(r.status == "active" for r in active)
    assert any(r.id == r1.id for r in active)
