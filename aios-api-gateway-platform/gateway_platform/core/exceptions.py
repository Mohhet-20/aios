"""Exception hierarchy for the Enterprise API Gateway, Integration Hub
& Service Mesh Platform."""
from __future__ import annotations


class GatewayPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(GatewayPlatformError):
    pass


class ValidationError(GatewayPlatformError):
    pass


class ConflictError(GatewayPlatformError):
    pass


class ConcurrentModificationError(GatewayPlatformError):
    pass


class AuthorizationError(GatewayPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    pass


class InvalidTransitionError(GatewayPlatformError):
    """Raised on an illegal lifecycle transition (route, service
    registration, circuit breaker, traffic rule, event subscription,
    webhook delivery, integration connection, API key)."""


# -- gateway core ---------------------------------------------------------------------------------

class GatewayError(GatewayPlatformError):
    pass


class RouteNotFoundError(GatewayError):
    pass


class RouteAlreadyExistsError(GatewayError):
    pass


class UnsupportedProtocolError(GatewayError):
    pass


class UnsupportedVisibilityError(GatewayError):
    pass


# -- api management ---------------------------------------------------------------------------------

class ApiManagementError(GatewayPlatformError):
    pass


class ApiKeyNotFoundError(ApiManagementError):
    pass


class ApiKeyRevokedError(ApiManagementError):
    pass


class ApiKeyExpiredError(ApiManagementError):
    pass


class QuotaExceededError(ApiManagementError):
    pass


class RateLimitExceededError(ApiManagementError):
    pass


class ApiVersionNotFoundError(ApiManagementError):
    pass


class ApiVersionRetiredError(ApiManagementError):
    pass


class JwtValidationError(ApiManagementError):
    pass


class SchemaValidationError(ApiManagementError):
    pass


class OAuthClientNotFoundError(ApiManagementError):
    pass


# -- service mesh ---------------------------------------------------------------------------------

class ServiceMeshError(GatewayPlatformError):
    pass


class ServiceNotFoundError(ServiceMeshError):
    pass


class ServiceInstanceNotFoundError(ServiceMeshError):
    pass


class NoHealthyInstancesError(ServiceMeshError):
    pass


class CircuitBreakerOpenError(ServiceMeshError):
    pass


class CircuitBreakerNotFoundError(ServiceMeshError):
    pass


class ConnectionPoolExhaustedError(ServiceMeshError):
    pass


# -- traffic management ---------------------------------------------------------------------------------

class TrafficError(GatewayPlatformError):
    pass


class TrafficRuleNotFoundError(TrafficError):
    pass


class InvalidTrafficWeightError(TrafficError):
    pass


# -- event platform ---------------------------------------------------------------------------------

class EventError(GatewayPlatformError):
    pass


class TopicNotFoundError(EventError):
    pass


class SubscriptionNotFoundError(EventError):
    pass


class EventNotFoundError(EventError):
    pass


class EventReplayWindowExceededError(EventError):
    pass


# -- integration hub ---------------------------------------------------------------------------------

class IntegrationError(GatewayPlatformError):
    pass


class ConnectorNotFoundError(IntegrationError):
    pass


class UnsupportedConnectorTypeError(IntegrationError):
    pass


class ConnectionNotFoundError(IntegrationError):
    pass


class WebhookNotFoundError(IntegrationError):
    pass


class WebhookDeliveryFailedError(IntegrationError):
    pass


# -- protocol translation ---------------------------------------------------------------------------------

class ProtocolTranslationError(GatewayPlatformError):
    pass


class UnsupportedTranslationPairError(ProtocolTranslationError):
    pass


class TranslationConfigNotFoundError(ProtocolTranslationError):
    pass


# -- security ---------------------------------------------------------------------------------

class GatewaySecurityError(GatewayPlatformError):
    pass


class RequestSignatureInvalidError(GatewaySecurityError):
    pass


class IpBlockedError(GatewaySecurityError):
    pass


class GeoBlockedError(GatewaySecurityError):
    pass


class SecurityPolicyNotFoundError(GatewaySecurityError):
    pass


class ThreatDetectedError(GatewaySecurityError):
    pass


# -- observability / analytics / topology ---------------------------------------------------------------------------------

class ObservabilityError(GatewayPlatformError):
    pass


class MetricNotFoundError(ObservabilityError):
    pass


# -- developer experience ---------------------------------------------------------------------------------

class DevExperienceError(GatewayPlatformError):
    pass


class SdkGenerationFailedError(DevExperienceError):
    pass


class TestConsoleRequestFailedError(DevExperienceError):
    pass
