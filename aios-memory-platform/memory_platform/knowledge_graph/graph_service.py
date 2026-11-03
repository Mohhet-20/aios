"""KnowledgeGraphService — a real, queryable graph over entities
(documents/projects/users/agents/workflows/concepts/topics/knowledge
items/memory entries/anything else via `entity_type='custom'`) and
typed relationships between them, backed by `KGEntityModel`/
`KGRelationshipModel` (two flat tables today — the documented seam a
future dedicated graph database, e.g. Neo4j, replaces without callers
changing). Provides the operations an in-DB graph substrate needs to be
useful: neighbor lookup, multi-hop BFS traversal, and shortest path —
not just CRUD on nodes and edges.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from memory_platform.database.base import new_uuid
from memory_platform.models.knowledge_graph import KGEntityModel, KGRelationshipModel
from memory_platform.repositories.registry import RepositoryRegistry


@dataclass
class GraphTraversalResult:
    root_entity_id: str
    visited_entity_ids: list[str]
    edges: list[KGRelationshipModel] = field(default_factory=list)
    depth_by_entity_id: dict[str, int] = field(default_factory=dict)


class KnowledgeGraphService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- entities --------------------------------------------------------------------

    async def upsert_entity(
        self, *, workspace_id: str, entity_type: str, name: str, ref_id: str | None = None, description: str | None = None, metadata: dict | None = None,
    ) -> KGEntityModel:
        """Idempotent by (workspace_id, entity_type, ref_id) when `ref_id`
        is given — mirroring an underlying row (a document, a knowledge
        item, a memory entry) should map to exactly one graph entity, not
        a new one every time it's touched. Entities with no `ref_id`
        (pure concepts/topics) are always created fresh."""
        if ref_id is not None:
            existing = await self.repos.kg_entities.get_by_ref(workspace_id, entity_type, ref_id)
            if existing is not None:
                existing.name = name
                if description is not None:
                    existing.description = description
                if metadata is not None:
                    existing.entity_metadata = metadata
                return await self.repos.kg_entities.update(existing)
        return await self.repos.kg_entities.add(KGEntityModel(
            id=new_uuid(), workspace_id=workspace_id, entity_type=entity_type, name=name, ref_id=ref_id,
            description=description, entity_metadata=metadata or {},
        ))

    async def get_entity(self, entity_id: str) -> KGEntityModel:
        return await self.repos.kg_entities.get_or_404(entity_id)

    async def get_entity_by_ref(self, workspace_id: str, entity_type: str, ref_id: str) -> KGEntityModel | None:
        return await self.repos.kg_entities.get_by_ref(workspace_id, entity_type, ref_id)

    async def list_entities_by_type(self, workspace_id: str, entity_type: str) -> list[KGEntityModel]:
        return await self.repos.kg_entities.list_by_type(workspace_id, entity_type)

    async def search_entities(self, workspace_id: str, query: str, *, limit: int = 50) -> list[KGEntityModel]:
        return await self.repos.kg_entities.search_by_name(workspace_id, query, limit=limit)

    async def delete_entity(self, entity_id: str) -> None:
        entity = await self.repos.kg_entities.get_or_404(entity_id)
        for rel in await self.repos.kg_relationships.list_touching(entity_id):
            await self.repos.kg_relationships.delete(rel, hard=True)
        await self.repos.kg_entities.delete(entity, hard=True)

    # -- relationships --------------------------------------------------------------------

    async def link(self, *, workspace_id: str, source_entity_id: str, target_entity_id: str, relation_type: str, weight: float = 1.0, metadata: dict | None = None) -> KGRelationshipModel:
        return await self.repos.kg_relationships.add(KGRelationshipModel(
            id=new_uuid(), workspace_id=workspace_id, source_entity_id=source_entity_id, target_entity_id=target_entity_id,
            relation_type=relation_type, weight=weight, relationship_metadata=metadata or {},
        ))

    async def unlink(self, relationship_id: str) -> None:
        rel = await self.repos.kg_relationships.get_or_404(relationship_id)
        await self.repos.kg_relationships.delete(rel, hard=True)

    async def relationships_for_workspace(self, workspace_id: str) -> list[KGRelationshipModel]:
        return await self.repos.kg_relationships.list_for_workspace(workspace_id)

    # -- graph queries --------------------------------------------------------------------

    async def neighbors(self, entity_id: str, *, direction: str = "both", relation_type: str | None = None) -> list[KGEntityModel]:
        """Direct (1-hop) neighbors."""
        neighbor_ids = await self._neighbor_ids(entity_id, direction=direction, relation_type=relation_type)
        return await self.repos.kg_entities.get_many(list(neighbor_ids))

    async def _neighbor_ids(self, entity_id: str, *, direction: str, relation_type: str | None) -> set[str]:
        neighbor_ids: set[str] = set()
        if direction in ("out", "both"):
            for rel in await self.repos.kg_relationships.list_outgoing(entity_id, relation_type=relation_type):
                neighbor_ids.add(rel.target_entity_id)
        if direction in ("in", "both"):
            for rel in await self.repos.kg_relationships.list_incoming(entity_id, relation_type=relation_type):
                neighbor_ids.add(rel.source_entity_id)
        neighbor_ids.discard(entity_id)
        return neighbor_ids

    async def traverse(self, entity_id: str, *, max_depth: int = 2, direction: str = "both", relation_type: str | None = None) -> GraphTraversalResult:
        """Real BFS multi-hop traversal — visits each entity at most once
        (cycle-safe, since a real graph can have cycles), stopping at
        `max_depth` hops from the root."""
        visited: dict[str, int] = {entity_id: 0}
        edges: list[KGRelationshipModel] = []
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            if direction in ("out", "both"):
                for rel in await self.repos.kg_relationships.list_outgoing(current_id, relation_type=relation_type):
                    edges.append(rel)
                    if rel.target_entity_id not in visited:
                        visited[rel.target_entity_id] = depth + 1
                        queue.append((rel.target_entity_id, depth + 1))
            if direction in ("in", "both"):
                for rel in await self.repos.kg_relationships.list_incoming(current_id, relation_type=relation_type):
                    edges.append(rel)
                    if rel.source_entity_id not in visited:
                        visited[rel.source_entity_id] = depth + 1
                        queue.append((rel.source_entity_id, depth + 1))

        return GraphTraversalResult(root_entity_id=entity_id, visited_entity_ids=list(visited.keys()), edges=edges, depth_by_entity_id=visited)

    async def shortest_path(self, source_entity_id: str, target_entity_id: str, *, max_depth: int = 8) -> list[str] | None:
        """Real BFS shortest path (unweighted — fewest hops), not a
        heuristic. Returns the entity-id path including both endpoints,
        or None if unreachable within `max_depth` hops."""
        if source_entity_id == target_entity_id:
            return [source_entity_id]

        visited = {source_entity_id}
        queue: deque[tuple[str, list[str]]] = deque([(source_entity_id, [source_entity_id])])
        depth = 0

        while queue and depth < max_depth:
            depth += 1
            for _ in range(len(queue)):
                current_id, path = queue.popleft()
                neighbor_ids = await self._neighbor_ids(current_id, direction="both", relation_type=None)
                for nid in neighbor_ids:
                    if nid == target_entity_id:
                        return path + [nid]
                    if nid not in visited:
                        visited.add(nid)
                        queue.append((nid, path + [nid]))
        return None

    # -- convenience wrappers over WellKnownRelationType --------------------------------

    async def dependencies(self, entity_id: str) -> list[KGEntityModel]:
        return await self.neighbors(entity_id, direction="out", relation_type="depends_on")

    async def semantic_links(self, entity_id: str) -> list[KGEntityModel]:
        return await self.neighbors(entity_id, direction="both", relation_type="similar_to")
