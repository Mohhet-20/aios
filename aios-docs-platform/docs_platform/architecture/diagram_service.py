"""Architecture Portal: a diagram registry across the seven diagram
types the prompt specifies (system overview, sequence, component,
deployment, infrastructure map, service map, dependency graph).
`related_diagrams` treats every diagram's `related_refs` list as one
edge set and BFS-traverses it, so "what else should I read to
understand this" works across the whole registry, not just one
diagram's direct links."""
from __future__ import annotations

from docs_platform.architecture.graph_rules import bfs_traverse
from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import DiagramNotFoundError, UnsupportedDiagramTypeError
from docs_platform.models.architecture import DiagramModel
from docs_platform.repositories.registry import RepositoryRegistry


class DiagramService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, diagram_id: str) -> DiagramModel:
        diagram = await self.repos.diagrams.get_or_404(diagram_id)
        if diagram.tenant_id != tenant_id:
            raise DiagramNotFoundError(f"Diagram '{diagram_id}' not found for tenant '{tenant_id}'")
        return diagram

    async def create_diagram(
        self, tenant_id: str, *, diagram_type: str, title: str, description: str = "",
        content: str = "", related_refs: list[str] | None = None, version: str = "v1",
    ) -> DiagramModel:
        if diagram_type not in self.settings.diagram_types:
            raise UnsupportedDiagramTypeError(f"Unsupported diagram type '{diagram_type}'")
        diagram = DiagramModel(
            tenant_id=tenant_id, diagram_type=diagram_type, title=title, description=description,
            content=content, related_refs=related_refs or [], version=version,
        )
        return await self.repos.diagrams.add(diagram)

    async def list_diagrams(self, tenant_id: str, *, diagram_type: str | None = None) -> list[DiagramModel]:
        return await self.repos.diagrams.list_for_tenant(tenant_id, diagram_type=diagram_type)

    async def related_diagrams(self, tenant_id: str, diagram_id: str) -> list[DiagramModel]:
        """`related_refs` is authored as a one-directional pointer (a
        diagram lists what it was built from or references), but
        "related to" is inherently a symmetric relationship for the
        reader — so this builds a bidirectional adjacency from every
        diagram's `related_refs` edges before traversing, rather than
        only following the direction the edge happened to be authored
        in."""
        await self.get_or_404(tenant_id, diagram_id)
        all_diagrams = await self.list_diagrams(tenant_id)
        adjacency: dict[str, list[str]] = {d.id: [] for d in all_diagrams}
        for d in all_diagrams:
            for ref in d.related_refs:
                if ref in adjacency:
                    adjacency[d.id].append(ref)
                    adjacency[ref].append(d.id)
        related_ids = bfs_traverse(adjacency, diagram_id)
        by_id = {d.id: d for d in all_diagrams}
        return [by_id[rid] for rid in related_ids if rid in by_id]
