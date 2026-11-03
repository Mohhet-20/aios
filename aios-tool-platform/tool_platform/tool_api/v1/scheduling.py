"""Task Scheduler: create immediate/delayed/calendar/recurring/cron
schedules, pause/resume/cancel them, and manually trigger a dispatcher
tick — the "Scheduled Execution" surface. A production deployment calls
`/scheduling/tick` from a timer (cron job, systemd timer, k8s
CronJob); this router doesn't own that timer itself."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.dependencies.dependencies import get_schedule_dispatcher, get_schedule_service
from tool_platform.scheduler.dispatcher import ScheduleDispatcher
from tool_platform.scheduler.schedule_service import ScheduleService
from tool_platform.tool_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/schedules", tags=["scheduling"])


class CreateImmediateRequest(BaseModel):
    tool_id: str
    workspace_id: str
    created_by: str
    input_data: dict = {}
    priority: str = "normal"


class CreateDelayedRequest(CreateImmediateRequest):
    run_at: datetime


class CreateRecurringRequest(BaseModel):
    tool_id: str
    workspace_id: str
    created_by: str
    interval_seconds: int
    start_at: datetime | None = None
    input_data: dict = {}
    priority: str = "normal"
    max_concurrent_executions: int | None = None
    rate_limit_per_minute: int | None = None


class CreateCronRequest(BaseModel):
    tool_id: str
    workspace_id: str
    created_by: str
    cron_expression: str
    input_data: dict = {}
    priority: str = "normal"
    max_concurrent_executions: int | None = None
    rate_limit_per_minute: int | None = None


@router.post("/immediate", status_code=201)
async def create_immediate(body: CreateImmediateRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.create_immediate(body.tool_id, body.workspace_id, created_by=body.created_by, input_data=body.input_data, priority=body.priority))


@router.post("/delayed", status_code=201)
async def create_delayed(body: CreateDelayedRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.create_delayed(body.tool_id, body.workspace_id, run_at=body.run_at, created_by=body.created_by, input_data=body.input_data, priority=body.priority))


@router.post("/recurring", status_code=201)
async def create_recurring(body: CreateRecurringRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.create_recurring(
        body.tool_id, body.workspace_id, interval_seconds=body.interval_seconds, created_by=body.created_by,
        start_at=body.start_at, input_data=body.input_data, priority=body.priority,
        max_concurrent_executions=body.max_concurrent_executions, rate_limit_per_minute=body.rate_limit_per_minute,
    ))


@router.post("/cron", status_code=201)
async def create_cron(body: CreateCronRequest, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.create_cron(
        body.tool_id, body.workspace_id, cron_expression=body.cron_expression, created_by=body.created_by,
        input_data=body.input_data, priority=body.priority, max_concurrent_executions=body.max_concurrent_executions,
        rate_limit_per_minute=body.rate_limit_per_minute,
    ))


@router.get("")
async def list_for_tool(tool_id: str, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict_list(await svc.list_for_tool(tool_id))


@router.post("/{schedule_id}/pause")
async def pause(schedule_id: str, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.pause(schedule_id))


@router.post("/{schedule_id}/resume")
async def resume(schedule_id: str, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.resume(schedule_id))


@router.post("/{schedule_id}/cancel")
async def cancel(schedule_id: str, svc: ScheduleService = Depends(get_schedule_service)):
    return to_dict(await svc.cancel(schedule_id))


@router.post("/tick")
async def tick(limit: int = 100, dispatcher: ScheduleDispatcher = Depends(get_schedule_dispatcher)):
    started = await dispatcher.tick(limit=limit)
    return {"started_count": len(started), "executions": to_dict_list(started)}
