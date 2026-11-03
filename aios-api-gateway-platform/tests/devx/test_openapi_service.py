from __future__ import annotations

from gateway_platform.devx.openapi_service import OpenApiSpecService
from gateway_platform.models.gateway import ApiRouteModel

TENANT = "devx-openapi-tenant"


def _route(**overrides):
    defaults = dict(
        tenant_id=TENANT, path="/orders", method="GET", protocol="rest", visibility="external",
        target_service="orders-service", status="active", description="List orders", tags=["orders"],
    )
    defaults.update(overrides)
    return ApiRouteModel(**defaults)


def test_build_spec_includes_active_routes():
    service = OpenApiSpecService()
    routes = [_route(), _route(path="/orders/{id}", method="DELETE", status="active")]
    spec = service.build_spec(TENANT, routes)
    assert spec["openapi"] == "3.0.3"
    assert "/orders" in spec["paths"]
    assert "get" in spec["paths"]["/orders"]
    assert "delete" in spec["paths"]["/orders/{id}"]


def test_build_spec_excludes_retired_routes():
    service = OpenApiSpecService()
    routes = [_route(status="retired")]
    spec = service.build_spec(TENANT, routes)
    assert spec["paths"] == {}
