"""EvaluationRun lifecycle: start a run bound to an evaluation's
current published version, then execute it against its dataset. The
API executes runs through the config-driven `ReferenceTargetExecutor`
(see `execution/executor.py`) — a real prompt/agent/workflow/model
backend is wired in by constructing an `EvaluationRunService` with a
different `TargetExecutor` in-process (e.g. the Agent/Workflow
Platform bridges in `agent_workflow/`), not by adding executor choice
to this HTTP surface, since a live backend call isn't something a
stateless JSON request can carry."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.dependencies.dependencies import get_evaluation_run_service
from eval_platform.eval_api.serialization import to_dict, to_dict_list
from eval_platform.execution.evaluation_run_service import EvaluationRunService
from eval_platform.execution.executor import ReferenceTargetExecutor

router = APIRouter(prefix="/runs", tags=["evaluation runs"])
_executor = ReferenceTargetExecutor()


class StartRunRequest(BaseModel):
    evaluation_id: str
    triggered_by: str | None = None
    trigger_type: str = "manual"
    max_retries: int = 0
    timeout_seconds: int = 120


@router.post("", status_code=201)
async def start_run(body: StartRunRequest, service: EvaluationRunService = Depends(get_evaluation_run_service)):
    return to_dict(await service.start_run(
        body.evaluation_id, triggered_by=body.triggered_by, trigger_type=body.trigger_type,
        max_retries=body.max_retries, timeout_seconds=body.timeout_seconds,
    ))


@router.post("/{run_id}/execute")
async def execute_run(run_id: str, service: EvaluationRunService = Depends(get_evaluation_run_service)):
    return to_dict(await service.execute_run(run_id, _executor))


@router.get("/{run_id}")
async def get_run(run_id: str, service: EvaluationRunService = Depends(get_evaluation_run_service)):
    return to_dict(await service.get_run(run_id))


@router.get("")
async def list_runs(evaluation_id: str, service: EvaluationRunService = Depends(get_evaluation_run_service)):
    return to_dict_list(await service.list_runs(evaluation_id))


@router.get("/{run_id}/item-results")
async def list_item_results(run_id: str, service: EvaluationRunService = Depends(get_evaluation_run_service)):
    return to_dict_list(await service.list_item_results(run_id))
