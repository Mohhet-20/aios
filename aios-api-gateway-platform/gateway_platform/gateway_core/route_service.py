"""Gateway core: the API route registry every inbound request is
matched against. One row per (path, method, protocol) triple, with a
guarded draft -> active -> deprecated <-> active -> retired lifecycle
(a deprecated route can be reactivated — undeprecating something that
turned out to still be needed shouldn't require recreating it)."""
from __future__ import annotations

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import (
    RouteAlreadyExistsError,
    RouteNotFoundError,
    UnsupportedProtocolError,
    UnsupportedVisibilityError,
)
from gateway_platform.domain.enums import RouteStatus
from gateway_platform.gateway_core.mappers import api_route_to_domain, apply_api_route_domain_to_model
from gateway_platform.models.gateway import ApiRouteModel
from gateway_platform.repositories.registry import RepositoryRegistry


class RouteRegistrationService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_supported(self, *, protocol: str, visibility: str) -> None:
        if protocol not in self.settings.gateway_supported_protocols:
            raise UnsupportedProtocolError(f"'{protocol}' is not a supported gateway protocol")
        if visibility not in self.settings.gateway_supported_visibilities:
            raise UnsupportedVisibilityError(f"'{visibility}' is not a supported route visibility")

    async def register_route(
        self, tenant_id: str, *, path: str, method: str = "GET", protocol: str = "rest", visibility: str = "internal",
        target_service: str, description: str | None = None, timeout_ms: int | None = None, tags: list | None = None,
    ) -> ApiRouteModel:
        self._assert_supported(protocol=protocol, visibility=visibility)
        existing = await self.repos.api_routes.get_by_path_method(tenant_id, path, method.upper())
        if existing is not None:
            raise RouteAlreadyExistsError(f"route '{method.upper()} {path}' already registered for tenant '{tenant_id}'")
        route = ApiRouteModel(
            tenant_id=tenant_id, path=path, method=method.upper(), protocol=protocol, visibility=visibility,
            target_service=target_service, status=RouteStatus.DRAFT.value, description=description,
            timeout_ms=timeout_ms or self.settings.gateway_default_timeout_ms, tags=tags or [],
        )
        return await self.repos.api_routes.add(route)

    async def activate_route(self, tenant_id: str, route_id: str) -> ApiRouteModel:
        route = await self._get_or_404(tenant_id, route_id)
        entity = api_route_to_domain(route)
        entity.activate()
        apply_api_route_domain_to_model(entity, route)
        return await self.repos.api_routes.update(route)

    async def deprecate_route(self, tenant_id: str, route_id: str) -> ApiRouteModel:
        route = await self._get_or_404(tenant_id, route_id)
        entity = api_route_to_domain(route)
        entity.deprecate()
        apply_api_route_domain_to_model(entity, route)
        return await self.repos.api_routes.update(route)

    async def reactivate_route(self, tenant_id: str, route_id: str) -> ApiRouteModel:
        route = await self._get_or_404(tenant_id, route_id)
        entity = api_route_to_domain(route)
        entity.activate()
        apply_api_route_domain_to_model(entity, route)
        return await self.repos.api_routes.update(route)

    async def retire_route(self, tenant_id: str, route_id: str) -> ApiRouteModel:
        route = await self._get_or_404(tenant_id, route_id)
        entity = api_route_to_domain(route)
        entity.retire()
        apply_api_route_domain_to_model(entity, route)
        return await self.repos.api_routes.update(route)

    async def match_route(self, tenant_id: str, path: str, method: str) -> ApiRouteModel:
        route = await self.repos.api_routes.get_by_path_method(tenant_id, path, method.upper())
        if route is None or route.status == RouteStatus.RETIRED.value:
            raise RouteNotFoundError(f"no active route for '{method.upper()} {path}'")
        return route

    async def list_routes(self, tenant_id: str, *, status: str | None = None) -> list[ApiRouteModel]:
        return await self.repos.api_routes.list_for_tenant(tenant_id, status=status)

    async def _get_or_404(self, tenant_id: str, route_id: str) -> ApiRouteModel:
        route = await self.repos.api_routes.get_or_404(route_id)
        if route.tenant_id != tenant_id:
            raise RouteNotFoundError(f"route '{route_id}' not found for tenant '{tenant_id}'")
        return route
