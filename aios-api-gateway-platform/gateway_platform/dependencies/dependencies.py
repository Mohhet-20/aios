"""FastAPI dependency wiring: DB session -> RepositoryRegistry ->
every service. Auth is intentionally minimal here, matching every
sibling AIOS platform: this platform expects to sit behind an
already-authenticated gateway (in practice, the Identity Platform)
that forwards the caller's tenant via `X-Tenant-Id` and, where
relevant, the acting principal via `X-User-Id`. Every service is
built fresh per request off a per-request `RepositoryRegistry`/
`AsyncSession`, since a session must never be shared across
concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from gateway_platform.api_management.api_key_service import ApiKeyService
from gateway_platform.api_management.jwt_service import JwtService
from gateway_platform.api_management.oauth_client_service import OAuthClientService
from gateway_platform.api_management.quota_service import QuotaService
from gateway_platform.api_management.rate_limit_service import RateLimiterService
from gateway_platform.api_management.schema_service import SchemaValidationService
from gateway_platform.api_management.version_service import ApiVersionService
from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.database.session import session_scope
from gateway_platform.devx.codegen_service import SdkCodeGenService
from gateway_platform.devx.openapi_service import OpenApiSpecService
from gateway_platform.devx.sample_service import SampleRequestService
from gateway_platform.devx.testing_console_service import TestingConsoleService
from gateway_platform.devx.webhook_testing_service import WebhookTestingService
from gateway_platform.events.event_bus_service import EventBusService
from gateway_platform.events.subscription_service import EventSubscriptionService
from gateway_platform.events.topic_service import EventTopicService
from gateway_platform.gateway_core.route_service import RouteRegistrationService
from gateway_platform.gateway_security.geo_filter_service import GeoFilterService
from gateway_platform.gateway_security.ip_filter_service import IpFilterService
from gateway_platform.gateway_security.policy_service import SecurityPolicyService
from gateway_platform.gateway_security.request_signing_service import RequestSigningService
from gateway_platform.gateway_security.security_event_service import SecurityEventService
from gateway_platform.gateway_security.threat_detection_service import ThreatDetectionService
from gateway_platform.integrations.connection_service import IntegrationConnectionService
from gateway_platform.integrations.connector_service import ConnectorService
from gateway_platform.observability.analytics_service import AnalyticsSnapshotService
from gateway_platform.observability.metrics_service import GatewayMetricsService
from gateway_platform.observability.topology_service import DependencyTopologyService
from gateway_platform.protocols.config_service import ProtocolTranslationConfigService
from gateway_platform.protocols.translation_service import ProtocolTranslationService
from gateway_platform.repositories.registry import RepositoryRegistry
from gateway_platform.service_mesh.circuit_breaker_service import CircuitBreakerService
from gateway_platform.service_mesh.health_check_service import HealthCheckService
from gateway_platform.service_mesh.load_balancer_service import LoadBalancerService
from gateway_platform.service_mesh.registry_service import ServiceRegistryService
from gateway_platform.traffic.traffic_rule_service import TrafficRuleService
from gateway_platform.webhooks.delivery_service import WebhookDeliveryService
from gateway_platform.webhooks.subscription_service import WebhookSubscriptionService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session, scope="function")) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — some
    of what this platform tracks (health sweeps, scheduled retention,
    automated retries) legitimately comes from a process with no
    human actor behind it."""
    return x_user_id


# -- gateway core -------------------------------------------------------------------------------
async def get_route_service(repos: RepositoryRegistry = Depends(get_repos)) -> RouteRegistrationService:
    return RouteRegistrationService(repos)


# -- api management -------------------------------------------------------------------------------
async def get_api_key_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApiKeyService:
    return ApiKeyService(repos)


async def get_rate_limiter_service(repos: RepositoryRegistry = Depends(get_repos)) -> RateLimiterService:
    return RateLimiterService(repos)


async def get_quota_service(repos: RepositoryRegistry = Depends(get_repos)) -> QuotaService:
    return QuotaService(repos)


async def get_api_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApiVersionService:
    return ApiVersionService(repos)


async def get_jwt_service() -> JwtService:
    return JwtService()


async def get_oauth_client_service(repos: RepositoryRegistry = Depends(get_repos)) -> OAuthClientService:
    return OAuthClientService(repos)


async def get_schema_validation_service(repos: RepositoryRegistry = Depends(get_repos)) -> SchemaValidationService:
    return SchemaValidationService(repos)


# -- service mesh ---------------------------------------------------------------------------------
async def get_service_registry_service(repos: RepositoryRegistry = Depends(get_repos)) -> ServiceRegistryService:
    return ServiceRegistryService(repos)


async def get_load_balancer_service(repos: RepositoryRegistry = Depends(get_repos)) -> LoadBalancerService:
    return LoadBalancerService(repos)


async def get_circuit_breaker_service(repos: RepositoryRegistry = Depends(get_repos)) -> CircuitBreakerService:
    return CircuitBreakerService(repos)


async def get_health_check_service(repos: RepositoryRegistry = Depends(get_repos)) -> HealthCheckService:
    return HealthCheckService(repos)


# -- traffic management -----------------------------------------------------------------------------
async def get_traffic_rule_service(repos: RepositoryRegistry = Depends(get_repos)) -> TrafficRuleService:
    return TrafficRuleService(repos)


# -- event platform ---------------------------------------------------------------------------------
async def get_event_topic_service(repos: RepositoryRegistry = Depends(get_repos)) -> EventTopicService:
    return EventTopicService(repos)


async def get_event_subscription_service(repos: RepositoryRegistry = Depends(get_repos)) -> EventSubscriptionService:
    return EventSubscriptionService(repos)


async def get_event_bus_service(repos: RepositoryRegistry = Depends(get_repos)) -> EventBusService:
    return EventBusService(repos)


# -- integration hub --------------------------------------------------------------------------------
async def get_connector_service(repos: RepositoryRegistry = Depends(get_repos)) -> ConnectorService:
    return ConnectorService(repos)


async def get_integration_connection_service(repos: RepositoryRegistry = Depends(get_repos)) -> IntegrationConnectionService:
    return IntegrationConnectionService(repos)


# -- webhooks -----------------------------------------------------------------------------------------
async def get_webhook_subscription_service(repos: RepositoryRegistry = Depends(get_repos)) -> WebhookSubscriptionService:
    return WebhookSubscriptionService(repos)


async def get_webhook_delivery_service(repos: RepositoryRegistry = Depends(get_repos)) -> WebhookDeliveryService:
    return WebhookDeliveryService(repos)


# -- protocol translation ----------------------------------------------------------------------------
async def get_protocol_translation_config_service(repos: RepositoryRegistry = Depends(get_repos)) -> ProtocolTranslationConfigService:
    return ProtocolTranslationConfigService(repos)


async def get_protocol_translation_service(repos: RepositoryRegistry = Depends(get_repos)) -> ProtocolTranslationService:
    return ProtocolTranslationService(repos)


# -- security -------------------------------------------------------------------------------------------
async def get_security_policy_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecurityPolicyService:
    return SecurityPolicyService(repos)


async def get_ip_filter_service(repos: RepositoryRegistry = Depends(get_repos)) -> IpFilterService:
    return IpFilterService(repos)


async def get_geo_filter_service(repos: RepositoryRegistry = Depends(get_repos)) -> GeoFilterService:
    return GeoFilterService(repos)


async def get_request_signing_service() -> RequestSigningService:
    return RequestSigningService()


async def get_threat_detection_service() -> ThreatDetectionService:
    return ThreatDetectionService()


async def get_security_event_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecurityEventService:
    return SecurityEventService(repos)


# -- observability / analytics / topology ------------------------------------------------------------------
async def get_gateway_metrics_service(repos: RepositoryRegistry = Depends(get_repos)) -> GatewayMetricsService:
    return GatewayMetricsService(repos)


async def get_dependency_topology_service(repos: RepositoryRegistry = Depends(get_repos)) -> DependencyTopologyService:
    return DependencyTopologyService(repos)


async def get_analytics_snapshot_service(repos: RepositoryRegistry = Depends(get_repos)) -> AnalyticsSnapshotService:
    return AnalyticsSnapshotService(repos)


# -- developer experience -----------------------------------------------------------------------------------
async def get_openapi_spec_service() -> OpenApiSpecService:
    return OpenApiSpecService()


async def get_sample_request_service() -> SampleRequestService:
    return SampleRequestService()


async def get_sdk_codegen_service(repos: RepositoryRegistry = Depends(get_repos)) -> SdkCodeGenService:
    return SdkCodeGenService(repos)


async def get_testing_console_service(repos: RepositoryRegistry = Depends(get_repos)) -> TestingConsoleService:
    return TestingConsoleService(repos)


async def get_webhook_testing_service() -> WebhookTestingService:
    return WebhookTestingService()
