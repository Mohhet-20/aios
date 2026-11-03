"""Task Scheduler surface: create immediate/delayed/calendar/recurring/cron
schedules, manage their lifecycle, and manually trigger a dispatcher tick
(the "actually fire due schedules" side normally run by a background loop)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.scheduler.dispatcher import SchedulerDispatcher
from workflow_platform.scheduler.scheduler_service import ScheduleService
from workflow_platform.workflow_api.dependencies import get_repos, get_schedule_service, get_scheduler_dispatcher
from workflow_platform.workflow_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/schedules", tags=["schedules"])


class CreateImmediateRequest(BaseModel):
    workflow_id: str
    workspace_id: str
    created_by: str
    input_variables: dict = {}
    priority: str = "normal"


class CreateDelayedRequest(CreateImmediateRequest):
    run_at: datetime


class CreateRecurringRequest(CreateImmediateRequest):
    interval_seconds: int
    start_at: datetime | None = None
    max_concurrent_executions: int | None = None
    rate_limit_per_minute: int | None = None


class CreateCronRequest(CreateImmediateRequest):
    cron_expression: str
    max_concurrent_executions: int | None = None
    rate_limit_per_minute: int | None = None


class SetDependencyRequest(BaseModel):
    depends_on_schedule_id: str | None = None


@router.post("/immediate", status_code=201)
async def create_immediate(body: CreateImmediateRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.create_immediate(body.workflow_id, body.workspace_id, created_by=body.created_by, input_variables=body.input_variables, priority=body.priority))


@router.post("/delayed", status_code=201)
async def create_delayed(body: CreateDelayedRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.create_delayed(body.workflow_id, body.workspace_id, run_at=body.run_at, created_by=body.created_by, input_variables=body.input_variables, priority=body.priority))


@router.post("/calendar", status_code=201)
async def create_calendar(body: CreateDelayedRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.create_calendar(body.workflow_id, body.workspace_id, run_at=body.run_at, created_by=body.created_by, input_variables=body.input_variables, priority=body.priority))


@router.post("/recurring", status_code=201)
async def create_recurring(body: CreateRecurringRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.create_recurring(
        body.workflow_id, body.workspace_id, interval_seconds=body.interval_seconds, created_by=body.created_by,
        start_at=body.start_at, input_variables=body.input_variables, priority=body.priority,
        max_concurrent_executions=body.max_concurrent_executions, rate_limit_per_minute=body.rate_limit_per_minute,
    ))


@router.post("/cron", status_code=201)
async def create_cron(body: CreateCronRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.create_cron(
        body.workflow_id, body.workspace_id, cron_expression=body.cron_expression, created_by=body.created_by,
        input_variables=body.input_variables, priority=body.priority,
        max_concurrent_executions=body.max_concurrent_executions, rate_limit_per_minute=body.rate_limit_per_minute,
    ))


@router.post("/{schedule_id}/dependency")
async def set_dependency(schedule_id: str, body: SetDependencyRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.set_dependency(schedule_id, body.depends_on_schedule_id))


@router.post("/{schedule_id}/pause")
async def pause_schedule(schedule_id: str, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.pause(schedule_id))


@router.post("/{schedule_id}/resume")
async def resume_schedule(schedule_id: str, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.resume(schedule_id))


@router.post("/{schedule_id}/cancel")
async def cancel_schedule(schedule_id: str, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.cancel(schedule_id))


@router.get("")
async def list_schedules(workflow_id: str, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict_list(await svc.list_for_workflow(workflow_id))


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.schedules.get_or_404(schedule_id))


@router.post("/dispatch/tick")
async def dispatch_tick(limit: int = 100, dispatcher: SchedulerDispatcher = Depends(get_scheduler_dispatcher)):
    fired = await dispatcher.tick(limit=limit)
    return {"fired_count": len(fired), "executions": to_dict_list(fired)}
