"""Pure-Python domain entities with guarded state machines — no ORM
imports. Each entity mirrors the `status`/`state` column on its ORM
model; services translate ORM <-> entity, apply a transition, and
persist the resulting status back. Same pattern as every prior AIOS
platform. Simpler status-only resources (service registrations,
service instances, traffic rules, event topics/subscriptions, webhook
subscriptions, OAuth clients, security policies) are guarded directly
in-service instead — the same precedent set by the Infrastructure and
Developer Platforms for lightly-stated resources."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from gateway_platform.core.exceptions import InvalidTransitionError
from gateway_platform.domain.enums import (
    ApiKeyStatus,
    ApiVersionStatus,
    CircuitBreakerState,
    ConnectionStatus,
    EventMessageStatus,
    RouteStatus,
    SdkGenStatus,
    WebhookDeliveryStatus,
)
from gateway_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# -- ApiRoute -------------------------------------------------------------------------------------

_ROUTE_TRANSITIONS: dict[RouteStatus, set[RouteStatus]] = {
    RouteStatus.DRAFT: {RouteStatus.ACTIVE},
    RouteStatus.ACTIVE: {RouteStatus.DEPRECATED},
    RouteStatus.DEPRECATED: {RouteStatus.ACTIVE, RouteStatus.RETIRED},
    RouteStatus.RETIRED: set(),
}


@dataclass
class ApiRoute:
    id: str
    status: RouteStatus = RouteStatus.DRAFT

    def _transition(self, target: RouteStatus) -> None:
        allowed = _ROUTE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ApiRoute '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def activate(self) -> None:
        self._transition(RouteStatus.ACTIVE)

    def deprecate(self) -> None:
        self._transition(RouteStatus.DEPRECATED)

    def retire(self) -> None:
        self._transition(RouteStatus.RETIRED)


# -- ApiKey -------------------------------------------------------------------------------------

_API_KEY_TRANSITIONS: dict[ApiKeyStatus, set[ApiKeyStatus]] = {
    ApiKeyStatus.ACTIVE: {ApiKeyStatus.REVOKED, ApiKeyStatus.EXPIRED},
    ApiKeyStatus.REVOKED: set(),
    ApiKeyStatus.EXPIRED: set(),
}


@dataclass
class ApiKey:
    id: str
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE

    def _transition(self, target: ApiKeyStatus) -> None:
        allowed = _API_KEY_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ApiKey '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def revoke(self) -> None:
        self._transition(ApiKeyStatus.REVOKED)

    def expire(self) -> None:
        self._transition(ApiKeyStatus.EXPIRED)


# -- ApiVersion -------------------------------------------------------------------------------------

_API_VERSION_TRANSITIONS: dict[ApiVersionStatus, set[ApiVersionStatus]] = {
    ApiVersionStatus.ACTIVE: {ApiVersionStatus.DEPRECATED},
    ApiVersionStatus.DEPRECATED: {ApiVersionStatus.RETIRED},
    ApiVersionStatus.RETIRED: set(),
}


@dataclass
class ApiVersion:
    id: str
    status: ApiVersionStatus = ApiVersionStatus.ACTIVE
    sunset_at: datetime | None = None

    def _transition(self, target: ApiVersionStatus) -> None:
        allowed = _API_VERSION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ApiVersion '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def deprecate(self, *, sunset_at: datetime) -> None:
        self._transition(ApiVersionStatus.DEPRECATED)
        self.sunset_at = sunset_at

    def retire(self) -> None:
        self._transition(ApiVersionStatus.RETIRED)


# -- CircuitBreaker -------------------------------------------------------------------------------------

_CIRCUIT_BREAKER_TRANSITIONS: dict[CircuitBreakerState, set[CircuitBreakerState]] = {
    CircuitBreakerState.CLOSED: {CircuitBreakerState.OPEN},
    CircuitBreakerState.OPEN: {CircuitBreakerState.HALF_OPEN},
    CircuitBreakerState.HALF_OPEN: {CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN},
}


@dataclass
class CircuitBreaker:
    id: str
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    opened_at: datetime | None = None
    half_opened_at: datetime | None = None

    def _transition(self, target: CircuitBreakerState) -> None:
        allowed = _CIRCUIT_BREAKER_TRANSITIONS.get(self.state, set())
        if target not in allowed:
            raise InvalidTransitionError(f"CircuitBreaker '{self.id}' cannot transition from {self.state.value} to {target.value}")
        self.state = target

    def trip(self) -> None:
        self._transition(CircuitBreakerState.OPEN)
        self.opened_at = _now()

    def half_open(self) -> None:
        self._transition(CircuitBreakerState.HALF_OPEN)
        self.half_opened_at = _now()

    def close(self) -> None:
        self._transition(CircuitBreakerState.CLOSED)
        self.opened_at = None
        self.half_opened_at = None


# -- EventMessage -------------------------------------------------------------------------------------

_EVENT_MESSAGE_TRANSITIONS: dict[EventMessageStatus, set[EventMessageStatus]] = {
    EventMessageStatus.PUBLISHED: {EventMessageStatus.DELIVERED, EventMessageStatus.FAILED},
    EventMessageStatus.FAILED: {EventMessageStatus.PUBLISHED, EventMessageStatus.DEAD_LETTERED},
    EventMessageStatus.DELIVERED: set(),
    EventMessageStatus.DEAD_LETTERED: set(),
}


@dataclass
class EventMessage:
    id: str
    status: EventMessageStatus = EventMessageStatus.PUBLISHED
    delivered_at: datetime | None = None

    def _transition(self, target: EventMessageStatus) -> None:
        allowed = _EVENT_MESSAGE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"EventMessage '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def deliver(self) -> None:
        self._transition(EventMessageStatus.DELIVERED)
        self.delivered_at = _now()

    def fail(self) -> None:
        self._transition(EventMessageStatus.FAILED)

    def retry(self) -> None:
        self._transition(EventMessageStatus.PUBLISHED)

    def dead_letter(self) -> None:
        self._transition(EventMessageStatus.DEAD_LETTERED)


# -- WebhookDelivery -------------------------------------------------------------------------------------

_WEBHOOK_DELIVERY_TRANSITIONS: dict[WebhookDeliveryStatus, set[WebhookDeliveryStatus]] = {
    WebhookDeliveryStatus.PENDING: {WebhookDeliveryStatus.DELIVERED, WebhookDeliveryStatus.FAILED},
    WebhookDeliveryStatus.FAILED: {WebhookDeliveryStatus.RETRYING, WebhookDeliveryStatus.DEAD_LETTERED},
    WebhookDeliveryStatus.RETRYING: {WebhookDeliveryStatus.DELIVERED, WebhookDeliveryStatus.FAILED},
    WebhookDeliveryStatus.DELIVERED: set(),
    WebhookDeliveryStatus.DEAD_LETTERED: set(),
}


@dataclass
class WebhookDelivery:
    id: str
    status: WebhookDeliveryStatus = WebhookDeliveryStatus.PENDING
    delivered_at: datetime | None = None

    def _transition(self, target: WebhookDeliveryStatus) -> None:
        allowed = _WEBHOOK_DELIVERY_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"WebhookDelivery '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def deliver(self) -> None:
        self._transition(WebhookDeliveryStatus.DELIVERED)
        self.delivered_at = _now()

    def fail(self) -> None:
        self._transition(WebhookDeliveryStatus.FAILED)

    def retry(self) -> None:
        self._transition(WebhookDeliveryStatus.RETRYING)

    def dead_letter(self) -> None:
        self._transition(WebhookDeliveryStatus.DEAD_LETTERED)


# -- IntegrationConnection -------------------------------------------------------------------------------------

_CONNECTION_TRANSITIONS: dict[ConnectionStatus, set[ConnectionStatus]] = {
    ConnectionStatus.PENDING: {ConnectionStatus.CONNECTED, ConnectionStatus.ERROR},
    ConnectionStatus.CONNECTED: {ConnectionStatus.ERROR, ConnectionStatus.DISCONNECTED},
    ConnectionStatus.ERROR: {ConnectionStatus.CONNECTED, ConnectionStatus.DISCONNECTED},
    ConnectionStatus.DISCONNECTED: set(),
}


@dataclass
class IntegrationConnection:
    id: str
    status: ConnectionStatus = ConnectionStatus.PENDING

    def _transition(self, target: ConnectionStatus) -> None:
        allowed = _CONNECTION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"IntegrationConnection '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def connect(self) -> None:
        self._transition(ConnectionStatus.CONNECTED)

    def error(self) -> None:
        self._transition(ConnectionStatus.ERROR)

    def disconnect(self) -> None:
        self._transition(ConnectionStatus.DISCONNECTED)


# -- SdkGenJob -------------------------------------------------------------------------------------

_SDK_GEN_JOB_TRANSITIONS: dict[SdkGenStatus, set[SdkGenStatus]] = {
    SdkGenStatus.QUEUED: {SdkGenStatus.RUNNING},
    SdkGenStatus.RUNNING: {SdkGenStatus.COMPLETED, SdkGenStatus.FAILED},
    SdkGenStatus.COMPLETED: set(),
    SdkGenStatus.FAILED: set(),
}


@dataclass
class SdkGenJob:
    id: str
    status: SdkGenStatus = SdkGenStatus.QUEUED

    def _transition(self, target: SdkGenStatus) -> None:
        allowed = _SDK_GEN_JOB_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"SdkGenJob '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(SdkGenStatus.RUNNING)

    def complete(self) -> None:
        self._transition(SdkGenStatus.COMPLETED)

    def fail(self) -> None:
        self._transition(SdkGenStatus.FAILED)
