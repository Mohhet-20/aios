"""ORM <-> domain-aggregate bridges for `ApiKey` and `ApiVersion`."""
from __future__ import annotations

from gateway_platform.domain.entities import ApiKey, ApiVersion
from gateway_platform.domain.enums import ApiKeyStatus, ApiVersionStatus
from gateway_platform.models.api_management import ApiKeyModel, ApiVersionModel


def api_key_to_domain(model: ApiKeyModel) -> ApiKey:
    return ApiKey(id=model.id, status=ApiKeyStatus(model.status))


def apply_api_key_domain_to_model(entity: ApiKey, model: ApiKeyModel) -> None:
    model.status = entity.status.value


def api_version_to_domain(model: ApiVersionModel) -> ApiVersion:
    return ApiVersion(id=model.id, status=ApiVersionStatus(model.status), sunset_at=model.sunset_at)


def apply_api_version_domain_to_model(entity: ApiVersion, model: ApiVersionModel) -> None:
    model.status = entity.status.value
    model.sunset_at = entity.sunset_at
