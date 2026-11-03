"""CLI Platform: session auth + command execution log."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.cli_platform.command_log_service import CliCommandLogService
from developer_platform.cli_platform.session_service import CliSessionService
from developer_platform.dependencies.dependencies import (
    get_cli_command_log_service,
    get_cli_session_service,
    get_current_tenant_id,
)
from developer_platform.dev_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/cli/sessions", tags=["cli-platform"])


class StartSessionRequest(BaseModel):
    developer_id: str
    api_key: str | None = None


@router.post("", status_code=201)
async def start_cli_session(
    body: StartSessionRequest, tenant_id: str = Depends(get_current_tenant_id), service: CliSessionService = Depends(get_cli_session_service),
):
    result = await service.start_session(tenant_id, developer_id=body.developer_id)
    return {"cli_token": result.raw_token, "developer_id": body.developer_id, "session": to_dict(result.session)}


class VerifyCliSessionRequest(BaseModel):
    cli_token: str


@router.post("/verify")
async def verify_cli_session(body: VerifyCliSessionRequest, service: CliSessionService = Depends(get_cli_session_service)):
    """Verifying also "touches" the session — `verify_session` bumps
    `last_seen_at` as a side effect, so there is no separate touch
    endpoint; a CLI heartbeat and an auth check are the same operation."""
    return to_dict(await service.verify_session(body.cli_token))


@router.post("/{session_id}/revoke")
async def revoke_cli_session(session_id: str, service: CliSessionService = Depends(get_cli_session_service)):
    return to_dict(await service.revoke_session(session_id))


@router.get("/for-developer/{developer_id}")
async def list_sessions_for_developer(
    developer_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CliSessionService = Depends(get_cli_session_service),
):
    return to_dict_list(await service.list_for_developer(tenant_id, developer_id))


commands_router = APIRouter(prefix="/cli/commands", tags=["cli-platform"])


class LogCommandRequest(BaseModel):
    session_id: str
    command: str
    args: dict = {}
    exit_code: int = 0


@commands_router.post("", status_code=201)
async def log_command(
    body: LogCommandRequest, tenant_id: str = Depends(get_current_tenant_id), service: CliCommandLogService = Depends(get_cli_command_log_service),
):
    return to_dict(await service.log_command(tenant_id, **body.model_dump()))


@commands_router.get("/for-session/{session_id}")
async def list_commands_for_session(
    session_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CliCommandLogService = Depends(get_cli_command_log_service),
):
    return to_dict_list(await service.list_for_session(tenant_id, session_id))
