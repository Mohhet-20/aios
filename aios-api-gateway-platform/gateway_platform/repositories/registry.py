"""Unit-of-work: one shared `AsyncSession` backing every repository,
lazily memoized. Identical pattern to every other AIOS platform."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from gateway_platform.repositories.api_management_repository import (
    ApiKeyRepository,
    ApiSchemaRepository,
    ApiUsageRecordRepository,
    ApiVersionRepository,
    OAuthClientRepository,
)
from gateway_platform.repositories.devx_repository import SdkGenJobRepository, TestConsoleRequestRepository
from gateway_platform.repositories.events_repository import (
    DeadLetterEntryRepository,
    EventMessageRepository,
    EventSubscriptionRepository,
    EventTopicRepository,
)
from gateway_platform.repositories.gateway_repository import ApiRouteRepository
from gateway_platform.repositories.integrations_repository import (
    ConnectorRepository,
    IntegrationConnectionRepository,
)
from gateway_platform.repositories.mesh_repository import (
    CircuitBreakerRepository,
    HealthCheckResultRepository,
    LoadBalancerPoolRepository,
    ServiceInstanceRepository,
    ServiceRegistrationRepository,
)
from gateway_platform.repositories.observability_repository import (
    AnalyticsSnapshotRepository,
    DependencyEdgeRepository,
    GatewayMetricRepository,
)
from gateway_platform.repositories.protocols_repository import ProtocolTranslationConfigRepository
from gateway_platform.repositories.security_repository import (
    GatewaySecurityPolicyRepository,
    GeoRuleRepository,
    IpRuleRepository,
    SecurityEventRepository,
)
from gateway_platform.repositories.traffic_repository import TrafficRuleRepository
from gateway_platform.repositories.webhooks_repository import (
    WebhookDeliveryRepository,
    WebhookSubscriptionRepository,
)


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, object] = {}

    def _get(self, key: str, cls):
        if key not in self._cache:
            self._cache[key] = cls(self.session)
        return self._cache[key]

    # -- gateway core --
    @property
    def api_routes(self) -> ApiRouteRepository:
        return self._get("api_routes", ApiRouteRepository)

    # -- api management --
    @property
    def api_keys(self) -> ApiKeyRepository:
        return self._get("api_keys", ApiKeyRepository)

    @property
    def api_usage_records(self) -> ApiUsageRecordRepository:
        return self._get("api_usage_records", ApiUsageRecordRepository)

    @property
    def api_versions(self) -> ApiVersionRepository:
        return self._get("api_versions", ApiVersionRepository)

    @property
    def oauth_clients(self) -> OAuthClientRepository:
        return self._get("oauth_clients", OAuthClientRepository)

    @property
    def api_schemas(self) -> ApiSchemaRepository:
        return self._get("api_schemas", ApiSchemaRepository)

    # -- service mesh --
    @property
    def services(self) -> ServiceRegistrationRepository:
        return self._get("services", ServiceRegistrationRepository)

    @property
    def service_instances(self) -> ServiceInstanceRepository:
        return self._get("service_instances", ServiceInstanceRepository)

    @property
    def load_balancer_pools(self) -> LoadBalancerPoolRepository:
        return self._get("load_balancer_pools", LoadBalancerPoolRepository)

    @property
    def circuit_breakers(self) -> CircuitBreakerRepository:
        return self._get("circuit_breakers", CircuitBreakerRepository)

    @property
    def health_check_results(self) -> HealthCheckResultRepository:
        return self._get("health_check_results", HealthCheckResultRepository)

    # -- traffic management --
    @property
    def traffic_rules(self) -> TrafficRuleRepository:
        return self._get("traffic_rules", TrafficRuleRepository)

    # -- event platform --
    @property
    def event_topics(self) -> EventTopicRepository:
        return self._get("event_topics", EventTopicRepository)

    @property
    def event_subscriptions(self) -> EventSubscriptionRepository:
        return self._get("event_subscriptions", EventSubscriptionRepository)

    @property
    def event_messages(self) -> EventMessageRepository:
        return self._get("event_messages", EventMessageRepository)

    @property
    def dead_letter_entries(self) -> DeadLetterEntryRepository:
        return self._get("dead_letter_entries", DeadLetterEntryRepository)

    # -- integration hub --
    @property
    def connectors(self) -> ConnectorRepository:
        return self._get("connectors", ConnectorRepository)

    @property
    def integration_connections(self) -> IntegrationConnectionRepository:
        return self._get("integration_connections", IntegrationConnectionRepository)

    # -- webhooks --
    @property
    def webhook_subscriptions(self) -> WebhookSubscriptionRepository:
        return self._get("webhook_subscriptions", WebhookSubscriptionRepository)

    @property
    def webhook_deliveries(self) -> WebhookDeliveryRepository:
        return self._get("webhook_deliveries", WebhookDeliveryRepository)

    # -- protocol translation --
    @property
    def protocol_translations(self) -> ProtocolTranslationConfigRepository:
        return self._get("protocol_translations", ProtocolTranslationConfigRepository)

    # -- security --
    @property
    def security_policies(self) -> GatewaySecurityPolicyRepository:
        return self._get("security_policies", GatewaySecurityPolicyRepository)

    @property
    def ip_rules(self) -> IpRuleRepository:
        return self._get("ip_rules", IpRuleRepository)

    @property
    def geo_rules(self) -> GeoRuleRepository:
        return self._get("geo_rules", GeoRuleRepository)

    @property
    def security_events(self) -> SecurityEventRepository:
        return self._get("security_events", SecurityEventRepository)

    # -- observability / analytics / topology --
    @property
    def gateway_metrics(self) -> GatewayMetricRepository:
        return self._get("gateway_metrics", GatewayMetricRepository)

    @property
    def dependency_edges(self) -> DependencyEdgeRepository:
        return self._get("dependency_edges", DependencyEdgeRepository)

    @property
    def analytics_snapshots(self) -> AnalyticsSnapshotRepository:
        return self._get("analytics_snapshots", AnalyticsSnapshotRepository)

    # -- developer experience --
    @property
    def sdk_gen_jobs(self) -> SdkGenJobRepository:
        return self._get("sdk_gen_jobs", SdkGenJobRepository)

    @property
    def test_console_requests(self) -> TestConsoleRequestRepository:
        return self._get("test_console_requests", TestConsoleRequestRepository)
