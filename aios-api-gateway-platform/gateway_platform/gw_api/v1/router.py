"""Aggregates every v1 router (health is mounted separately at the
app root, not under /api/v1) into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from gateway_platform.gw_api.v1 import (
    api_management,
    devx,
    events,
    gateway_core,
    gateway_security,
    integrations,
    observability,
    protocols,
    service_mesh,
    traffic,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(gateway_core.router)

api_router.include_router(api_management.router)
api_router.include_router(api_management.usage_router)
api_router.include_router(api_management.versions_router)
api_router.include_router(api_management.jwt_router)
api_router.include_router(api_management.oauth_router)
api_router.include_router(api_management.schemas_router)

api_router.include_router(service_mesh.router)
api_router.include_router(service_mesh.load_balancer_router)
api_router.include_router(service_mesh.circuit_breaker_router)
api_router.include_router(service_mesh.health_router)

api_router.include_router(traffic.router)

api_router.include_router(events.router)
api_router.include_router(events.subscriptions_router)
api_router.include_router(events.messages_router)

api_router.include_router(integrations.router)
api_router.include_router(integrations.connections_router)

api_router.include_router(webhooks.router)
api_router.include_router(webhooks.deliveries_router)

api_router.include_router(protocols.router)

api_router.include_router(gateway_security.router)
api_router.include_router(gateway_security.ip_filter_router)
api_router.include_router(gateway_security.geo_filter_router)
api_router.include_router(gateway_security.signing_router)
api_router.include_router(gateway_security.threat_router)
api_router.include_router(gateway_security.events_router)

api_router.include_router(observability.router)
api_router.include_router(observability.topology_router)
api_router.include_router(observability.analytics_router)

api_router.include_router(devx.router)
api_router.include_router(devx.samples_router)
api_router.include_router(devx.codegen_router)
api_router.include_router(devx.console_router)
api_router.include_router(devx.webhook_testing_router)
