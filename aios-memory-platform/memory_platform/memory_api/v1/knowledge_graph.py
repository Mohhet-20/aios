"""Knowledge Graph: entities and typed relationships over documents,
projects, users, agents, workflows, concepts, and topics — real BFS
neighbor/traversal/shortest-path queries against the in-DB substrate."""
from __future__ import annotations


from fastapi import APIRouter, Depends
from pydantic import BaseModel

from memory_platform.knowledge_graph.graph_service import KnowledgeGraphService
from memory_platform.memory_api.dependencies import get_knowledge_graph_service
from memory_platform.memory_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/workspaces/{workspace_id}/graph", tags=["knowledge-graph"])


class UpsertEntityRequest(BaseModel):
    entity_type: str
    name: str
    ref_id: str | None = None
    description: str | None = None
    metadata: dict | None = None


class LinkEntitiesRequest(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    weight: float = 1.0
    metadata: dict | None = None


@router.post("/entities", status_code=201)
async def upsert_entity(workspace_id: str, body: UpsertEntityRequest, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    return to_dict(await svc.upsert_entity(workspace_id=workspace_id, entity_type=body.entity_type, name=body.name, ref_id=body.ref_id, description=body.description, metadata=body.metadata))


@router.get("/entities/search")
async def search_entities(workspace_id: str, query: str, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    return to_dict_list(await svc.search_entities(workspace_id, query))


@router.get("/entities/by-type/{entity_type}")
async def list_entities_by_type(workspace_id: str, entity_type: str, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    return to_dict_list(await svc.list_entities_by_type(workspace_id, entity_type))


@router.get("/entities/{entity_id}")
async def get_entity(workspace_id: str, entity_id: str, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    return to_dict(await svc.get_entity(entity_id))


@router.delete("/entities/{entity_id}", status_code=204)
async def delete_entity(workspace_id: str, entity_id: str, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    await svc.delete_entity(entity_id)


@router.post("/relationships", status_code=201)
async def link_entities(workspace_id: str, body: LinkEntitiesRequest, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    return to_dict(await svc.link(workspace_id=workspace_id, source_entity_id=body.source_entity_id, target_entity_id=body.target_entity_id, relation_type=body.relation_type, weight=body.weight, metadata=body.metadata))


@router.delete("/relationships/{relationship_id}", status_code=204)
async def unlink_entities(workspace_id: str, relationship_id: str, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    await svc.unlink(relationship_id)


@router.get("/entities/{entity_id}/neighbors")
async def neighbors(workspace_id: str, entity_id: str, direction: str = "both", relation_type: str | None = None, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    return to_dict_list(await svc.neighbors(entity_id, direction=direction, relation_type=relation_type))


@router.get("/entities/{entity_id}/traverse")
async def traverse(workspace_id: str, entity_id: str, max_depth: int = 2, direction: str = "both", relation_type: str | None = None, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    result = await svc.traverse(entity_id, max_depth=max_depth, direction=direction, relation_type=relation_type)
    return {"root_entity_id": result.root_entity_id, "visited_entity_ids": result.visited_entity_ids, "depth_by_entity_id": result.depth_by_entity_id, "edges": to_dict_list(result.edges)}


@router.get("/entities/{entity_id}/shortest-path/{target_entity_id}")
async def shortest_path(workspace_id: str, entity_id: str, target_entity_id: str, max_depth: int = 8, svc: KnowledgeGraphService = Depends(get_knowledge_graph_service)):
    path = await svc.shortest_path(entity_id, target_entity_id, max_depth=max_depth)
    return {"path": path}
