"""Integration Hub: connector catalog + per-tenant connections."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import (
    get_connector_service,
    get_current_tenant_id,
    get_integration_connection_service,
)
from gateway_platform.gw_api.serialization import to_dict, to_dict_list
from gateway_platform.integrations.connection_service import IntegrationConnectionService
from gateway_platform.integrations.connector_service import ConnectorService

router = APIRouter(prefix="/integrations/connectors", tags=["integration-hub"])


class RegisterConnectorRequest(BaseModel):
    connector_type: str
    name: str
    config_schema: dict | None = None
    sync_interval_minutes: int | None = None


@router.post("", status_code=201)
async def register_connector(
    body: RegisterConnectorRequest, tenant_id: str = Depends(get_current_tenant_id), service: ConnectorService = Depends(get_connector_service),
):
    return to_dict(await service.register_connector(tenant_id, **body.model_dump()))


@router.get("")
async def list_connectors(tenant_id: str = Depends(get_current_tenant_id), service: ConnectorService = Depends(get_connector_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


connections_router = APIRouter(prefix="/integrations/connections", tags=["integration-hub"])


class CreateConnectionRequest(BaseModel):
    connector_id: str
    name: str
    credentials_ref: str | None = None
    config: dict | None = None


@connections_router.post("", status_code=201)
async def create_connection(
    body: CreateConnectionRequest, tenant_id: str = Depends(get_current_tenant_id), service: IntegrationConnectionService = Depends(get_integration_connection_service),
):
    payload = body.model_dump()
    connector_id = payload.pop("connector_id")
    return to_dict(await service.create_connection(tenant_id, connector_id, **payload))


@connections_router.post("/{connection_id}/mark-connected")
async def mark_connection_connected(
    connection_id: str, tenant_id: str = Depends(get_current_tenant_id), service: IntegrationConnectionService = Depends(get_integration_connection_service),
):
    return to_dict(await service.mark_connected(tenant_id, connection_id))


@connections_router.post("/{connection_id}/mark-error")
async def mark_connection_error(
    connection_id: str, tenant_id: str = Depends(get_current_tenant_id), service: IntegrationConnectionService = Depends(get_integration_connection_service),
):
    return to_dict(await service.mark_error(tenant_id, connection_id))


@connections_router.post("/{connection_id}/disconnect")
async def disconnect_connection(
    connection_id: str, tenant_id: str = Depends(get_current_tenant_id), service: IntegrationConnectionService = Depends(get_integration_connection_service),
):
    return to_dict(await service.disconnect(tenant_id, connection_id))


@connections_router.get("/for-connector/{connector_id}")
async def list_connections_for_connector(
    connector_id: str, tenant_id: str = Depends(get_current_tenant_id), service: IntegrationConnectionService = Depends(get_integration_connection_service),
):
    return to_dict_list(await service.list_for_connector(tenant_id, connector_id))


@connections_router.get("")
async def list_connections(tenant_id: str = Depends(get_current_tenant_id), service: IntegrationConnectionService = Depends(get_integration_connection_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))
