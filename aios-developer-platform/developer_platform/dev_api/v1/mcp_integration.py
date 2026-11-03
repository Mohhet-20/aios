"""MCP Integration: server registry, sessions with permission checks,
capability discovery. `POST /mcp/servers/{id}/discover` accepts a
discovery payload directly (resources/tools/prompts) rather than
requiring a live transport connection — the same "declared
capabilities" path `StaticTransportAdapter` exists for."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_mcp_discovery_service,
    get_mcp_server_service,
    get_mcp_session_service,
)
from developer_platform.dev_api.serialization import to_dict, to_dict_list
from developer_platform.mcp_integration.discovery_service import McpDiscoveryService
from developer_platform.mcp_integration.server_service import McpServerService
from developer_platform.mcp_integration.session_service import McpSessionService
from developer_platform.mcp_integration.transport import McpDiscoveryResult, StaticTransportAdapter

router = APIRouter(prefix="/mcp/servers", tags=["mcp-integration"])


class RegisterServerRequest(BaseModel):
    name: str
    transport: str = "stdio"
    endpoint_ref: str
    protocol_version: str = "2024-11-05"


@router.post("", status_code=201)
async def register_mcp_server(
    body: RegisterServerRequest, tenant_id: str = Depends(get_current_tenant_id), service: McpServerService = Depends(get_mcp_server_service),
):
    return to_dict(await service.register_server(tenant_id, **body.model_dump()))


@router.get("")
async def list_mcp_servers(tenant_id: str = Depends(get_current_tenant_id), service: McpServerService = Depends(get_mcp_server_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.post("/{server_id}/connect")
async def connect_mcp_server(server_id: str, tenant_id: str = Depends(get_current_tenant_id), service: McpServerService = Depends(get_mcp_server_service)):
    return to_dict(await service.connect(tenant_id, server_id))


@router.post("/{server_id}/disconnect")
async def disconnect_mcp_server(server_id: str, tenant_id: str = Depends(get_current_tenant_id), service: McpServerService = Depends(get_mcp_server_service)):
    return to_dict(await service.disconnect(tenant_id, server_id))


class DiscoveryPayload(BaseModel):
    resources: list[dict] = []
    tools: list[dict] = []
    prompts: list[dict] = []


@router.post("/{server_id}/discover")
async def discover_mcp_capabilities(
    server_id: str, body: DiscoveryPayload, tenant_id: str = Depends(get_current_tenant_id),
    service: McpDiscoveryService = Depends(get_mcp_discovery_service),
):
    adapter = StaticTransportAdapter(McpDiscoveryResult(**body.model_dump()))
    result = await service.discover_and_sync(tenant_id, server_id, adapter)
    return {
        "resources": to_dict_list(result.resources), "tools": to_dict_list(result.tools), "prompts": to_dict_list(result.prompts),
    }


sessions_router = APIRouter(prefix="/mcp/sessions", tags=["mcp-integration"])


class StartMcpSessionRequest(BaseModel):
    mcp_server_id: str
    client_id: str
    permissions: list[str] = []


@sessions_router.post("", status_code=201)
async def start_mcp_session(
    body: StartMcpSessionRequest, tenant_id: str = Depends(get_current_tenant_id), service: McpSessionService = Depends(get_mcp_session_service),
):
    return to_dict(await service.start_session(tenant_id, **body.model_dump()))


@sessions_router.post("/{session_id}/close")
async def close_mcp_session(session_id: str, tenant_id: str = Depends(get_current_tenant_id), service: McpSessionService = Depends(get_mcp_session_service)):
    return to_dict(await service.close_session(tenant_id, session_id))


class CheckPermissionRequest(BaseModel):
    required: str


@sessions_router.post("/{session_id}/check-permission")
async def check_mcp_permission(
    session_id: str, body: CheckPermissionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: McpSessionService = Depends(get_mcp_session_service),
):
    await service.check_permission(tenant_id, session_id, body.required)
    return {"allowed": True}


@sessions_router.get("")
async def list_active_mcp_sessions(tenant_id: str = Depends(get_current_tenant_id), service: McpSessionService = Depends(get_mcp_session_service)):
    return to_dict_list(await service.list_active(tenant_id))
