"""Execution control plane: start/run/pause/resume/cancel/retry a workflow
run, plus read access to executions and their node-execution history —
the core "run a workflow" surface of the orchestration engine."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.workflow_api.dependencies import get_execution_engine, get_repos
from workflow_platform.workflow_api.serialization import to_dict, to_dict_list
from workflow_platform.workflow_engine.engine import ExecutionEngine

router = APIRouter(prefix="/executions", tags=["executions"])


class StartExecutionRequest(BaseModel):
    workflow_id: str
    triggered_by: str | None = None
    trigger_type: str = "manual"
    input_variables: dict = {}
    priority: str = "normal"


class ApprovalResumeRequest(BaseModel):
    approved: bool
    output_data: dict | None = None


@router.post("", status_code=201)
async def start_execution(body: StartExecutionRequest, engine: ExecutionEngine = Depends(get_execution_engine)):
    execution = await engine.start_execution(
        body.workflow_id, triggered_by=body.triggered_by, trigger_type=body.trigger_type,
        input_variables=body.input_variables, priority=body.priority,
    )
    return to_dict(execution)


@router.get("/{execution_id}")
async def get_execution(execution_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.executions.get_or_404(execution_id))


@router.get("")
async def list_executions(workflow_id: str | None = None, workspace_id: str | None = None, status: str | None = None, repos: RepositoryRegistry = Depends(get_repos)):
    if workflow_id:
        return to_dict_list(await repos.executions.list_for_workflow(workflow_id, status=status))
    if workspace_id:
        return to_dict_list(await repos.executions.list_for_workspace(workspace_id, status=status))
    if status:
        return to_dict_list(await repos.executions.list_by_status(status))
    return []


@router.get("/{execution_id}/node-executions")
async def list_node_executions(execution_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict_list(await repos.node_executions.list_for_execution(execution_id))


@router.get("/{execution_id}/children")
async def list_children(execution_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict_list(await repos.executions.list_children(execution_id))


@router.post("/{execution_id}/pause")
async def pause_execution(execution_id: str, engine: ExecutionEngine = Depends(get_execution_engine)):
    return to_dict(await engine.pause_execution(execution_id))


@router.post("/{execution_id}/resume")
async def resume_execution(execution_id: str, engine: ExecutionEngine = Depends(get_execution_engine)):
    return to_dict(await engine.resume_execution(execution_id))


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str, engine: ExecutionEngine = Depends(get_execution_engine)):
    return to_dict(await engine.cancel_execution(execution_id))


@router.post("/{execution_id}/rollback")
async def rollback_execution(execution_id: str, engine: ExecutionEngine = Depends(get_execution_engine)):
    return to_dict(await engine.rollback(execution_id))


@router.post("/{execution_id}/resume-after-approval")
async def resume_after_approval(execution_id: str, body: ApprovalResumeRequest, engine: ExecutionEngine = Depends(get_execution_engine)):
    return to_dict(await engine.resume_after_approval(execution_id, approved=body.approved, output_data=body.output_data))


@router.post("/{execution_id}/retry-node/{node_key}")
async def retry_node(execution_id: str, node_key: str, engine: ExecutionEngine = Depends(get_execution_engine)):
    return to_dict(await engine.retry_node(execution_id, node_key))
