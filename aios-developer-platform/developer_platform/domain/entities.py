"""Pure-Python domain entities with guarded state machines — no ORM
imports. Each entity mirrors the `status`/`stage` column on its ORM
model; services translate ORM <-> entity, apply a transition, and
persist the resulting status back. Same pattern as every other AIOS
services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from developer_platform.core.exceptions import InvalidTransitionError
from developer_platform.domain.enums import (
    ApiKeyStatus,
    CodeGenStatus,
    PackageVersionStatus,
    PluginVersionStatus,
    SandboxStatus,
    WebhookDeliveryStatus,
)
from developer_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


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


# -- PluginVersion --------------------------------------------------------------------------

_PLUGIN_VERSION_TRANSITIONS: dict[PluginVersionStatus, set[PluginVersionStatus]] = {
    PluginVersionStatus.DRAFT: {PluginVersionStatus.VALIDATED},
    PluginVersionStatus.VALIDATED: {PluginVersionStatus.SIGNED, PluginVersionStatus.DRAFT},
    PluginVersionStatus.SIGNED: {PluginVersionStatus.PUBLISHED, PluginVersionStatus.DRAFT},
    PluginVersionStatus.PUBLISHED: {PluginVersionStatus.DEPRECATED},
    PluginVersionStatus.DEPRECATED: set(),
}


@dataclass
class PluginVersion:
    id: str
    status: PluginVersionStatus = PluginVersionStatus.DRAFT

    def _transition(self, target: PluginVersionStatus) -> None:
        allowed = _PLUGIN_VERSION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"PluginVersion '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def mark_validated(self) -> None:
        self._transition(PluginVersionStatus.VALIDATED)

    def invalidate(self) -> None:
        self._transition(PluginVersionStatus.DRAFT)

    def sign(self) -> None:
        self._transition(PluginVersionStatus.SIGNED)

    def publish(self) -> None:
        self._transition(PluginVersionStatus.PUBLISHED)

    def deprecate(self) -> None:
        self._transition(PluginVersionStatus.DEPRECATED)


# -- WebhookDelivery --------------------------------------------------------------------------

_WEBHOOK_DELIVERY_TRANSITIONS: dict[WebhookDeliveryStatus, set[WebhookDeliveryStatus]] = {
    WebhookDeliveryStatus.PENDING: {WebhookDeliveryStatus.DELIVERING},
    WebhookDeliveryStatus.DELIVERING: {WebhookDeliveryStatus.SUCCEEDED, WebhookDeliveryStatus.FAILED},
    WebhookDeliveryStatus.FAILED: {WebhookDeliveryStatus.DELIVERING, WebhookDeliveryStatus.EXHAUSTED},
    WebhookDeliveryStatus.SUCCEEDED: set(),
    WebhookDeliveryStatus.EXHAUSTED: set(),
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

    def start_delivery(self) -> None:
        self._transition(WebhookDeliveryStatus.DELIVERING)

    def succeed(self) -> None:
        self._transition(WebhookDeliveryStatus.SUCCEEDED)
        self.delivered_at = _now()

    def fail(self) -> None:
        self._transition(WebhookDeliveryStatus.FAILED)

    def exhaust(self) -> None:
        self._transition(WebhookDeliveryStatus.EXHAUSTED)


# -- CodeGenJob -------------------------------------------------------------------------------

_CODEGEN_JOB_TRANSITIONS: dict[CodeGenStatus, set[CodeGenStatus]] = {
    CodeGenStatus.QUEUED: {CodeGenStatus.RUNNING},
    CodeGenStatus.RUNNING: {CodeGenStatus.COMPLETED, CodeGenStatus.FAILED},
    CodeGenStatus.COMPLETED: set(),
    CodeGenStatus.FAILED: set(),
}


@dataclass
class CodeGenJob:
    id: str
    status: CodeGenStatus = CodeGenStatus.QUEUED
    finished_at: datetime | None = None

    def _transition(self, target: CodeGenStatus) -> None:
        allowed = _CODEGEN_JOB_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"CodeGenJob '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(CodeGenStatus.RUNNING)

    def complete(self) -> None:
        self._transition(CodeGenStatus.COMPLETED)
        self.finished_at = _now()

    def fail(self) -> None:
        self._transition(CodeGenStatus.FAILED)
        self.finished_at = _now()


# -- SandboxEnvironment -----------------------------------------------------------------------

_SANDBOX_TRANSITIONS: dict[SandboxStatus, set[SandboxStatus]] = {
    SandboxStatus.PROVISIONING: {SandboxStatus.RUNNING, SandboxStatus.TERMINATED},
    SandboxStatus.RUNNING: {SandboxStatus.EXPIRED, SandboxStatus.TERMINATED},
    SandboxStatus.EXPIRED: {SandboxStatus.TERMINATED},
    SandboxStatus.TERMINATED: set(),
}


@dataclass
class SandboxEnvironment:
    id: str
    status: SandboxStatus = SandboxStatus.PROVISIONING
    terminated_at: datetime | None = None

    def _transition(self, target: SandboxStatus) -> None:
        allowed = _SANDBOX_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"SandboxEnvironment '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def mark_running(self) -> None:
        self._transition(SandboxStatus.RUNNING)

    def expire(self) -> None:
        self._transition(SandboxStatus.EXPIRED)

    def terminate(self) -> None:
        self._transition(SandboxStatus.TERMINATED)
        self.terminated_at = _now()


# -- PackageVersion ---------------------------------------------------------------------------

_PACKAGE_VERSION_TRANSITIONS: dict[PackageVersionStatus, set[PackageVersionStatus]] = {
    PackageVersionStatus.DRAFT: {PackageVersionStatus.PUBLISHED},
    PackageVersionStatus.PUBLISHED: {PackageVersionStatus.DEPRECATED},
    PackageVersionStatus.DEPRECATED: set(),
}


@dataclass
class PackageVersion:
    id: str
    status: PackageVersionStatus = PackageVersionStatus.DRAFT
    published_at: datetime | None = None
    deprecated_at: datetime | None = None

    def _transition(self, target: PackageVersionStatus) -> None:
        allowed = _PACKAGE_VERSION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"PackageVersion '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def publish(self) -> None:
        self._transition(PackageVersionStatus.PUBLISHED)
        self.published_at = _now()

    def deprecate(self) -> None:
        self._transition(PackageVersionStatus.DEPRECATED)
        self.deprecated_at = _now()
