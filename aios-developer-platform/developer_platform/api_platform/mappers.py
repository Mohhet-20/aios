"""ORM <-> domain-aggregate bridge for `ApiKey`."""
from __future__ import annotations

from developer_platform.domain.entities import ApiKey
from developer_platform.domain.enums import ApiKeyStatus
from developer_platform.models.api_platform import ApiKeyModel


def api_key_to_domain(model: ApiKeyModel) -> ApiKey:
    return ApiKey(id=model.id, status=ApiKeyStatus(model.status))


def apply_api_key_domain_to_model(entity: ApiKey, model: ApiKeyModel) -> None:
    model.status = entity.status.value
