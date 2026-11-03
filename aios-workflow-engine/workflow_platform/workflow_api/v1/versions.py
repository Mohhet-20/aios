"""Workflow version graph editing (draft creation, node/edge CRUD,
publish/deprecate) and the node-type registry — the "Workflow Builder
Canvas" / "Node Library" frontend surfaces."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workflow_platform.node_library.registry import NODE_TYPE_SPECS, seed_node_definitions
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.workflow_api.dependencies import get_repos, get_version_service
from workflow_platform.workflow_api.serialization import to_dict, to_dict_list
from workflow_platform.workflow_core.version_service import WorkflowVersionService

router = APIRouter(tags=["versions"])


class CreateDraftRequest(BaseModel):
    created_by: str


class AddNodeRequest(BaseModel):
    node_key: str
    node_type: str
    name: str
    config: dict = {}
    position: dict = {}
    timeout_seconds: int | None = None
    max_retries: int | None = None


class AddEdgeRequest(BaseModel):
    source_node_key: str
    target_node_key: str
    condition: dict | None = None
    edge_metadata: dict = {}


class ReplaceGraphRequest(BaseModel):
    nodes: list[dict]
    edges: list[dict]


@router.post("/workflows/{workflow_id}/versions/draft", status_code=201)
async def get_or_create_draft(workflow_id: str, body: CreateDraftRequest, svc: WorkflowVersionService = Depends(get_version_service)):
    return to_dict(await svc.get_or_create_draft(workflow_id, created_by=body.created_by))


@router.get("/workflows/{workflow_id}/versions")
async def list_versions(workflow_id: str, svc: WorkflowVersionService = Depends(get_version_service)):
    return to_dict_list(await svc.list_versions(workflow_id))


@router.get("/versions/{version_id}")
async def get_version(version_id: str, svc: WorkflowVersionService = Depends(get_version_service)):
    return to_dict(await svc.get_version(version_id))


@router.get("/versions/{version_id}/graph")
async def get_graph(version_id: str, svc: WorkflowVersionService = Depends(get_version_service)):
    nodes, edges = await svc.get_graph(version_id)
    return {"nodes": to_dict_list(nodes), "edges": to_dict_list(edges)}


@router.post("/versions/{version_id}/nodes", status_code=201)
async def add_node(version_id: str, body: AddNodeRequest, svc: WorkflowVersionService = Depends(get_version_service)):
    return to_dict(await svc.add_node(
        version_id, node_key=body.node_key, node_type=body.node_type, name=body.name, config=body.config,
        position=body.position, timeout_seconds=body.timeout_seconds, max_retries=body.max_retries,
    ))


@router.delete("/versions/{version_id}/nodes/{node_key}", status_code=204)
async def remove_node(version_id: str, node_key: str, svc: WorkflowVersionService = Depends(get_version_service)):
    await svc.remove_node(version_id, node_key)


@router.post("/versions/{version_id}/edges", status_code=201)
async def add_edge(version_id: str, body: AddEdgeRequest, svc: WorkflowVersionService = Depends(get_version_service)):
    return to_dict(await svc.add_edge(
        version_id, source_node_key=body.source_node_key, target_node_key=body.target_node_key,
        condition=body.condition, edge_metadata=body.edge_metadata,
    ))


@router.delete("/edges/{edge_id}", status_code=204)
async def remove_edge(edge_id: str, svc: WorkflowVersionService = Depends(get_version_service)):
    await svc.remove_edge(edge_id)


@router.put("/versions/{version_id}/graph")
async def replace_graph(version_id: str, body: ReplaceGraphRequest, svc: WorkflowVersionService = Depends(get_version_service)):
    await svc.replace_graph(version_id, nodes=body.nodes, edges=body.edges)
    nodes, edges = await svc.get_graph(version_id)
    return {"nodes": to_dict_list(nodes), "edges": to_dict_list(edges)}


@router.post("/versions/{version_id}/publish")
async def publish_version(version_id: str, svc: WorkflowVersionService = Depends(get_version_service)):
    return to_dict(await svc.publish_version(version_id))


@router.post("/versions/{version_id}/deprecate")
async def deprecate_version(version_id: str, svc: WorkflowVersionService = Depends(get_version_service)):
    return to_dict(await svc.deprecate_version(version_id))


# -- node type registry ---------------------------------------------------------------

@router.get("/node-types")
async def list_node_types():
    return [
        {"key": s.key, "name": s.name, "description": s.description, "category": s.category, "input_schema": s.input_schema, "output_schema": s.output_schema}
        for s in NODE_TYPE_SPECS
    ]


@router.post("/node-types/seed", status_code=201)
async def seed_node_types(repos: RepositoryRegistry = Depends(get_repos)):
    inserted = await seed_node_definitions(repos)
    return {"inserted": inserted}


@router.get("/node-definitions")
async def list_node_definitions(repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict_list(await repos.node_definitions.list_all())
