"""AI Tool Planning: capability matching, input validation, automatic
tool selection + ranking, fallback chains, and multi-tool plan
composition/optimization — what an agent's tool-use loop calls before
it ever touches the Execution Engine."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.ai_planning.planning_service import ToolPlanningService
from tool_platform.dependencies.dependencies import get_planning_service
from tool_platform.tool_api.serialization import to_dict_list

router = APIRouter(prefix="/planning", tags=["planning"])


class SelectToolRequest(BaseModel):
    workspace_id: str
    query: str
    required_capabilities: list[str] | None = None


class ValidateInputRequest(BaseModel):
    tool_version_id: str
    input_data: dict


class BuildPlanRequest(BaseModel):
    steps: list[tuple[str, str, dict]]


@router.post("/match-capabilities")
async def match_capabilities(workspace_id: str, required_capabilities: list[str], svc: ToolPlanningService = Depends(get_planning_service)):
    return to_dict_list(await svc.match_capabilities(workspace_id, required_capabilities))


@router.post("/validate-input")
async def validate_input(body: ValidateInputRequest, svc: ToolPlanningService = Depends(get_planning_service)):
    error = await svc.validate_input(body.tool_version_id, body.input_data)
    return {"valid": error is None, "error": error}


@router.post("/select-tool")
async def select_tool(body: SelectToolRequest, svc: ToolPlanningService = Depends(get_planning_service)):
    ranked = await svc.select_tool(body.workspace_id, body.query, required_capabilities=body.required_capabilities)
    return [asdict(r) for r in ranked]


@router.post("/build-plan")
async def build_plan(body: BuildPlanRequest, svc: ToolPlanningService = Depends(get_planning_service)):
    plan = svc.build_plan(body.steps)
    return {"steps": [asdict(s) for s in plan.steps]}


@router.post("/optimize-plan")
async def optimize_plan(body: BuildPlanRequest, svc: ToolPlanningService = Depends(get_planning_service)):
    plan = svc.build_plan(body.steps)
    waves = svc.optimize_plan(plan)
    return {"waves": [[asdict(s) for s in wave] for wave in waves]}
