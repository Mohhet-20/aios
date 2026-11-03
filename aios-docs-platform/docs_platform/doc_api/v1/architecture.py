"""Architecture Portal: diagrams (system overview, sequence, component,
deployment, infra/service maps, dependency graphs) and the technology
stack registry."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.architecture.diagram_service import DiagramService
from docs_platform.architecture.tech_stack_service import TechStackService
from docs_platform.dependencies.dependencies import get_current_tenant_id, get_diagram_service, get_tech_stack_service
from docs_platform.doc_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/diagrams", tags=["architecture"])
tech_stack_router = APIRouter(prefix="/tech-stack", tags=["architecture"])


class CreateDiagramRequest(BaseModel):
    diagram_type: str
    title: str
    description: str = ""
    content: str = ""
    related_refs: list[str] | None = None
    version: str = "v1"


@router.post("", status_code=201)
async def create_diagram(
    body: CreateDiagramRequest, tenant_id: str = Depends(get_current_tenant_id), service: DiagramService = Depends(get_diagram_service),
):
    return to_dict(await service.create_diagram(tenant_id, **body.model_dump()))


@router.get("")
async def list_diagrams(
    diagram_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: DiagramService = Depends(get_diagram_service),
):
    return to_dict_list(await service.list_diagrams(tenant_id, diagram_type=diagram_type))


@router.get("/{diagram_id}")
async def get_diagram(
    diagram_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DiagramService = Depends(get_diagram_service),
):
    return to_dict(await service.get_or_404(tenant_id, diagram_id))


@router.get("/{diagram_id}/related")
async def get_related_diagrams(
    diagram_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DiagramService = Depends(get_diagram_service),
):
    return to_dict_list(await service.related_diagrams(tenant_id, diagram_id))


class AddTechStackEntryRequest(BaseModel):
    category: str
    name: str
    version_info: str = ""
    description: str = ""


@tech_stack_router.post("", status_code=201)
async def add_tech_stack_entry(
    body: AddTechStackEntryRequest, tenant_id: str = Depends(get_current_tenant_id), service: TechStackService = Depends(get_tech_stack_service),
):
    return to_dict(await service.add_entry(tenant_id, **body.model_dump()))


@tech_stack_router.get("")
async def list_tech_stack_entries(
    category: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: TechStackService = Depends(get_tech_stack_service),
):
    return to_dict_list(await service.list_entries(tenant_id, category=category))
