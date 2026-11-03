"""ORM <-> domain-aggregate bridge for `IntegrationConnection`."""
from __future__ import annotations

from gateway_platform.domain.entities import IntegrationConnection
from gateway_platform.domain.enums import ConnectionStatus
from gateway_platform.models.integrations import IntegrationConnectionModel


def connection_to_domain(model: IntegrationConnectionModel) -> IntegrationConnection:
    return IntegrationConnection(id=model.id, status=ConnectionStatus(model.status))


def apply_connection_domain_to_model(entity: IntegrationConnection, model: IntegrationConnectionModel) -> None:
    model.status = entity.status.value
