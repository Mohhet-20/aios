"""Dependency mapping / service topology API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.dependencies.dependencies import get_current_tenant_id, get_service_map_service, get_topology_dependency_service
from observability_platform.topology.dependency_service import TopologyDependencyService
from observability_platform.topology.service_map_service import ServiceMapService

router = APIRouter(prefix="/topology", tags=["topology"])


class RegisterNodeRequest(BaseModel):
    name: str
    node_type: str
    component_id: str | None = None
    metadata: dict | None = None


@router.post("/nodes", status_code=201)
async def register_node(body: RegisterNodeRequest, tenant_id: str = Depends(get_current_tenant_id), service: ServiceMapService = Depends(get_service_map_service)):
    node = await service.register_node(tenant_id, **body.model_dump())
    return {"id": node.id, "name": node.name, "node_type": node.node_type}


class AddEdgeRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    edge_type: str
    metadata: dict | None = None


@router.post("/edges", status_code=201)
async def add_edge(body: AddEdgeRequest, tenant_id: str = Depends(get_current_tenant_id), service: ServiceMapService = Depends(get_service_map_service)):
    edge = await service.add_edge(tenant_id, **body.model_dump())
    return {"id": edge.id, "source": edge.source_node_id, "target": edge.target_node_id, "edge_type": edge.edge_type}


@router.get("/map")
async def service_map(tenant_id: str = Depends(get_current_tenant_id), service: ServiceMapService = Depends(get_service_map_service)):
    return await service.get_service_map(tenant_id)


@router.get("/{node_id}/downstream-impact")
async def downstream_impact(node_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TopologyDependencyService = Depends(get_topology_dependency_service)):
    return {"impacted_node_ids": await service.downstream_impact(tenant_id, node_id)}


@router.get("/{node_id}/upstream-dependencies")
async def upstream_dependencies(node_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TopologyDependencyService = Depends(get_topology_dependency_service)):
    return {"dependency_node_ids": await service.upstream_dependencies(tenant_id, node_id)}
