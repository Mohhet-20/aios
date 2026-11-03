"""ORM <-> domain-aggregate bridge for `ApiKey`."""
from __future__ import annotations

from identity_platform.domain.entities import ApiKey
from identity_platform.domain.enums import ApiKeyStatus
from identity_platform.models.api_key import ApiKeyModel


def api_key_to_domain(model: ApiKeyModel) -> ApiKey:
    return ApiKey(id=model.id, status=ApiKeyStatus(model.status), revoked_reason=model.revoked_reason)


def apply_api_key_domain_to_model(entity: ApiKey, model: ApiKeyModel) -> None:
    model.status = entity.status.value
    model.revoked_reason = entity.revoked_reason
    model.revoked_at = entity.revoked_at
