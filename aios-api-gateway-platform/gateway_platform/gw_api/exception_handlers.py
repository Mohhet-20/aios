"""Maps the platform's domain exception hierarchy (core/exceptions.py)
to HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gateway_platform.core.exceptions import (
    ApiKeyExpiredError,
    ApiKeyNotFoundError,
    ApiKeyRevokedError,
    ApiManagementError,
    ApiVersionNotFoundError,
    ApiVersionRetiredError,
    AuthorizationError,
    CircuitBreakerNotFoundError,
    CircuitBreakerOpenError,
    ConcurrentModificationError,
    ConflictError,
    ConnectionNotFoundError,
    ConnectionPoolExhaustedError,
    ConnectorNotFoundError,
    EventError,
    EventNotFoundError,
    EventReplayWindowExceededError,
    GatewayError,
    GatewayPlatformError,
    GatewaySecurityError,
    GeoBlockedError,
    IntegrationError,
    InvalidTransitionError,
    IpBlockedError,
    JwtValidationError,
    MetricNotFoundError,
    NoHealthyInstancesError,
    NotFoundError,
    OAuthClientNotFoundError,
    ObservabilityError,
    PermissionDeniedError,
    ProtocolTranslationError,
    QuotaExceededError,
    RateLimitExceededError,
    RequestSignatureInvalidError,
    RouteAlreadyExistsError,
    RouteNotFoundError,
    SchemaValidationError,
    SdkGenerationFailedError,
    SecurityPolicyNotFoundError,
    ServiceInstanceNotFoundError,
    ServiceMeshError,
    ServiceNotFoundError,
    SubscriptionNotFoundError,
    TenantIsolationError,
    TestConsoleRequestFailedError,
    ThreatDetectedError,
    TopicNotFoundError,
    TrafficError,
    TrafficRuleNotFoundError,
    TranslationConfigNotFoundError,
    UnsupportedConnectorTypeError,
    UnsupportedProtocolError,
    UnsupportedTranslationPairError,
    UnsupportedVisibilityError,
    ValidationError,
    WebhookDeliveryFailedError,
    WebhookNotFoundError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[GatewayPlatformError], int]] = [
    (NotFoundError, 404),
    # gateway core
    (RouteNotFoundError, 404),
    (RouteAlreadyExistsError, 409),
    (UnsupportedProtocolError, 422),
    (UnsupportedVisibilityError, 422),
    (GatewayError, 400),
    # api management
    (ApiKeyNotFoundError, 404),
    (ApiKeyRevokedError, 401),
    (ApiKeyExpiredError, 401),
    (QuotaExceededError, 429),
    (RateLimitExceededError, 429),
    (ApiVersionNotFoundError, 404),
    (ApiVersionRetiredError, 410),
    (JwtValidationError, 401),
    (SchemaValidationError, 422),
    (OAuthClientNotFoundError, 404),
    (ApiManagementError, 400),
    # service mesh
    (ServiceInstanceNotFoundError, 404),
    (ServiceNotFoundError, 404),
    (NoHealthyInstancesError, 503),
    (CircuitBreakerOpenError, 503),
    (CircuitBreakerNotFoundError, 404),
    (ConnectionPoolExhaustedError, 503),
    (ServiceMeshError, 400),
    # traffic management
    (TrafficRuleNotFoundError, 404),
    (TrafficError, 422),
    # event platform
    (TopicNotFoundError, 404),
    (SubscriptionNotFoundError, 404),
    (EventNotFoundError, 404),
    (EventReplayWindowExceededError, 422),
    (EventError, 400),
    # integration hub / webhooks
    (ConnectorNotFoundError, 404),
    (UnsupportedConnectorTypeError, 422),
    (ConnectionNotFoundError, 404),
    (WebhookNotFoundError, 404),
    (WebhookDeliveryFailedError, 422),
    (IntegrationError, 400),
    # protocol translation
    (UnsupportedTranslationPairError, 422),
    (TranslationConfigNotFoundError, 404),
    (ProtocolTranslationError, 400),
    # security
    (RequestSignatureInvalidError, 401),
    (IpBlockedError, 403),
    (GeoBlockedError, 403),
    (SecurityPolicyNotFoundError, 404),
    (ThreatDetectedError, 403),
    (GatewaySecurityError, 400),
    # observability / analytics / topology
    (MetricNotFoundError, 404),
    (ObservabilityError, 400),
    # developer experience
    (SdkGenerationFailedError, 422),
    (TestConsoleRequestFailedError, 422),
    # base group
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: GatewayPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(GatewayPlatformError)
    async def _handle_platform_error(request: Request, exc: GatewayPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
