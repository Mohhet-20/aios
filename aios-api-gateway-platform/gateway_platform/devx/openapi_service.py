"""API Explorer / Swagger backing: builds a real OpenAPI 3.0.3 dict
from the platform's own route registry -- the same "docs and codegen
both consume one real spec builder" pattern the Developer Platform's
API Platform module established, scoped here to `ApiRouteModel`
instead of that platform's own key/version tables."""
from __future__ import annotations

from gateway_platform.models.gateway import ApiRouteModel


def _path_item(route: ApiRouteModel) -> dict:
    operation = {
        "summary": route.description or f"{route.method} {route.path}",
        "tags": route.tags or [route.target_service],
        "operationId": f"{route.method.lower()}_{route.id}",
        "responses": {"200": {"description": "Successful response"}},
    }
    return {route.method.lower(): operation}


class OpenApiSpecService:
    def build_spec(self, tenant_id: str, routes: list[ApiRouteModel], *, title: str = "AIOS API Gateway", version: str = "v1") -> dict:
        paths: dict[str, dict] = {}
        for route in routes:
            if route.status == "retired":
                continue
            paths.setdefault(route.path, {}).update(_path_item(route))

        return {
            "openapi": "3.0.3",
            "info": {"title": title, "version": version},
            "paths": paths,
        }
