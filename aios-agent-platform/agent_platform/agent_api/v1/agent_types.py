"""Agent Type registry — the 17 built-in types plus any custom types a
workspace defines. Seeding is idempotent (calling it twice is a no-op
for existing keys), which is what lets a fresh deployment bootstrap its
type catalogue with one call."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_platform.agent_api.dependencies import get_agent_type_service
from agent_platform.agent_api.serialization import to_dict, to_dict_list
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.domain.enums import AgentCategory

router = APIRouter(prefix="/agent-types", tags=["agent-types"])


class CreateAgentTypeRequest(BaseModel):
    key: str
    name: str
    category: str = "custom"
    description: str | None = None
    default_instructions: str = ""
    default_capabilities: list[str] = []
    default_skills: list[str] = []
    default_tool_names: list[str] = []
    default_resource_limits: dict = {}


@router.post("/seed-builtin", status_code=201)
async def seed_builtin_types(svc: AgentTypeService = Depends(get_agent_type_service)):
    return to_dict_list(await svc.seed_builtin_types())


@router.post("", status_code=201)
async def create_agent_type(body: CreateAgentTypeRequest, svc: AgentTypeService = Depends(get_agent_type_service)):
    fields = body.model_dump()
    fields["category"] = AgentCategory(fields["category"])
    agent_type = await svc.create_type(**fields)
    return to_dict(agent_type)


@router.get("")
async def list_agent_types(svc: AgentTypeService = Depends(get_agent_type_service)):
    return to_dict_list(await svc.list_types())


@router.get("/{key}")
async def get_agent_type(key: str, svc: AgentTypeService = Depends(get_agent_type_service)):
    return to_dict(await svc.get_by_key(key))
