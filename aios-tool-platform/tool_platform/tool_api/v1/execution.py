"""Tool call execution: start (sync/async/queued/batch/parallel),
control (cancel/retry/rollback), and history — the "Execution Console"
frontend surface. Every check the Execution Engine's constructor was
given (rate limit, concurrency quota, sensitive-tool approval gating,
audit logging) fires transparently here since `get_execution_engine`
wires all of it in by default."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.dependencies.dependencies import get_current_actor_id, get_execution_engine, get_repos
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.tool_api.serialization import to_dict, to_dict_list
from tool_platform.tool_execution.engine import ToolExecutionEngine

router = APIRouter(prefix="/executions", tags=["executions"])


class StartExecutionRequest(BaseModel):
    tool_id: str
    input_data: dict = {}
    execution_mode: str = "sync"
    trigger_type: str = "manual"
    priority: str = "normal"
    credential_id: str | None = None
    approval_gate_id: str | None = None


class RunBatchRequest(BaseModel):
    tool_id: str
    input_batches: list[dict]
    execution_mode: str = "parallel"
    credential_id: str | None = None
    max_concurrency: int | None = None


@router.post("", status_code=201)
async def start_execution(
    body: StartExecutionRequest, actor_id: str = Depends(get_current_actor_id),
    engine: ToolExecutionEngine = Depends(get_execution_engine),
):
    execution = await engine.start_execution(
        body.tool_id, input_data=body.input_data, execution_mode=body.execution_mode, triggered_by=actor_id,
        trigger_type=body.trigger_type, priority=body.priority, credential_id=body.credential_id,
        approval_gate_id=body.approval_gate_id,
    )
    return to_dict(execution)


@router.post("/batch", status_code=201)
async def run_batch(body: RunBatchRequest, actor_id: str = Depends(get_current_actor_id), engine: ToolExecutionEngine = Depends(get_execution_engine)):
    parent, children = await engine.run_batch(
        body.tool_id, body.input_batches, execution_mode=body.execution_mode, triggered_by=actor_id,
        credential_id=body.credential_id, max_concurrency=body.max_concurrency,
    )
    return {"parent": to_dict(parent), "children": to_dict_list(children)}


@router.get("/{execution_id}")
async def get_execution(execution_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.executions.get_or_404(execution_id))


@router.get("")
async def list_executions(
    tool_id: str | None = None, workspace_id: str | None = None, status: str | None = None,
    limit: int = 100, repos: RepositoryRegistry = Depends(get_repos),
):
    if tool_id:
        return to_dict_list(await repos.executions.list_for_tool(tool_id, status=status, limit=limit))
    if workspace_id:
        return to_dict_list(await repos.executions.list_for_workspace(workspace_id, status=status, limit=limit))
    return []


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str, engine: ToolExecutionEngine = Depends(get_execution_engine)):
    return to_dict(await engine.cancel_execution(execution_id))


@router.post("/{execution_id}/retry")
async def retry_execution(execution_id: str, engine: ToolExecutionEngine = Depends(get_execution_engine)):
    return to_dict(await engine.retry_execution(execution_id))


@router.post("/{execution_id}/rollback")
async def rollback_execution(execution_id: str, engine: ToolExecutionEngine = Depends(get_execution_engine)):
    return to_dict(await engine.rollback_execution(execution_id))
