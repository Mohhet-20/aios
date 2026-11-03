"""State Management surface: scoped variables (with secret encryption),
execution state/context snapshots, checkpoints, and stalled-execution
recovery."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workflow_platform.recovery.recovery_service import RecoveryService
from workflow_platform.state.execution_state_service import ExecutionStateService
from workflow_platform.state.variable_service import VariableService
from workflow_platform.workflow_api.dependencies import (
    get_execution_state_service,
    get_recovery_service,
    get_variable_service,
)
from workflow_platform.workflow_api.serialization import to_dict, to_dict_list

router = APIRouter(tags=["state"])


class SetVariableRequest(BaseModel):
    key: str
    value: object
    is_secret: bool = False


@router.put("/variables/{scope_type}/{scope_id}", status_code=201)
async def set_variable(scope_type: str, scope_id: str, body: SetVariableRequest, svc: VariableService = Depends(get_variable_service)):
    return to_dict(await svc.set_variable(scope_type, scope_id, body.key, body.value, is_secret=body.is_secret))


@router.get("/variables/{scope_type}/{scope_id}/{key}")
async def get_variable(scope_type: str, scope_id: str, key: str, svc: VariableService = Depends(get_variable_service)):
    return {"key": key, "value": await svc.get_variable(scope_type, scope_id, key)}


@router.delete("/variables/{scope_type}/{scope_id}/{key}", status_code=204)
async def delete_variable(scope_type: str, scope_id: str, key: str, svc: VariableService = Depends(get_variable_service)):
    await svc.delete_variable(scope_type, scope_id, key)


@router.get("/variables/{scope_type}/{scope_id}")
async def list_variables(scope_type: str, scope_id: str, svc: VariableService = Depends(get_variable_service)):
    return to_dict_list(await svc.list_for_scope(scope_type, scope_id))


@router.get("/executions/{execution_id}/state")
async def get_state_snapshot(execution_id: str, svc: ExecutionStateService = Depends(get_execution_state_service)):
    return await svc.get_state_snapshot(execution_id)


@router.get("/executions/{execution_id}/metadata")
async def get_execution_metadata(execution_id: str, svc: ExecutionStateService = Depends(get_execution_state_service)):
    return await svc.get_execution_metadata(execution_id)


@router.get("/executions/{execution_id}/checkpoints")
async def list_checkpoints(execution_id: str, svc: RecoveryService = Depends(get_recovery_service)):
    return to_dict_list(await svc.list_checkpoints(execution_id))


@router.get("/executions/{execution_id}/checkpoints/latest")
async def get_latest_checkpoint(execution_id: str, svc: RecoveryService = Depends(get_recovery_service)):
    return to_dict(await svc.get_latest_checkpoint(execution_id))


@router.post("/executions/{execution_id}/restore-checkpoint")
async def restore_from_checkpoint(execution_id: str, sequence_number: int | None = None, svc: RecoveryService = Depends(get_recovery_service)):
    return to_dict(await svc.restore_from_checkpoint(execution_id, sequence_number=sequence_number))


@router.post("/recovery/stalled")
async def recover_stalled_executions(stalled_after_seconds: int = 300, svc: RecoveryService = Depends(get_recovery_service)):
    recovered = await svc.recover_stalled_executions(stalled_after_seconds=stalled_after_seconds)
    return {"recovered_count": len(recovered), "executions": to_dict_list(recovered)}
