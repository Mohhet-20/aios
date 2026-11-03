"""ORM <-> domain-aggregate bridge for `ApiRoute`."""
from __future__ import annotations

from gateway_platform.domain.entities import ApiRoute
from gateway_platform.domain.enums import RouteStatus
from gateway_platform.models.gateway import ApiRouteModel


def api_route_to_domain(model: ApiRouteModel) -> ApiRoute:
    return ApiRoute(id=model.id, status=RouteStatus(model.status))


def apply_api_route_domain_to_model(entity: ApiRoute, model: ApiRouteModel) -> None:
    model.status = entity.status.value
