"""SearchService: global/workspace lexical search over asset name and
description, tag search, and metadata filtering. Semantic search is a
disclosed gap here, the same category as the Tool Platform's
undocumented connectors: this platform has no embedding model of its
own. `SemanticSearchProvider` is a `Protocol` with a
`NullSemanticSearchProvider` reference implementation that transparently
falls back to lexical search rather than raising or fabricating
similarity scores — swapping in a real provider backed by the AI
Core's embedding engine is a one-file change behind the same
interface, matching the platform-bridge pattern the Tool Platform
established for its own cross-platform integrations."""
from __future__ import annotations

from typing import Protocol

from collaboration_platform.models.asset import CollaborationAssetModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class SemanticSearchProvider(Protocol):
    async def search(self, query: str, candidates: list[CollaborationAssetModel]) -> list[CollaborationAssetModel]:
        """Returns `candidates` re-ranked by semantic relevance to `query`."""
        ...


class NullSemanticSearchProvider:
    """Reference implementation: no embedding model is wired up, so
    this returns `candidates` unchanged (already lexically ranked) —
    an honest no-op rather than a fabricated similarity ranking."""

    async def search(self, query: str, candidates: list[CollaborationAssetModel]) -> list[CollaborationAssetModel]:
        return candidates


class SearchService:
    def __init__(self, repos: RepositoryRegistry, *, semantic_provider: SemanticSearchProvider | None = None):
        self.repos = repos
        self.semantic_provider = semantic_provider or NullSemanticSearchProvider()

    async def search(
        self, query: str, *, workspace_id: str | None = None, asset_type: str | None = None, limit: int = 50, semantic: bool = False,
    ) -> list[CollaborationAssetModel]:
        results = await self.repos.assets.search_lexical(query, workspace_id=workspace_id, asset_type=asset_type, limit=limit)
        if semantic:
            results = await self.semantic_provider.search(query, results)
        return results

    async def search_by_tag(self, workspace_id: str, tag_name: str) -> list[CollaborationAssetModel]:
        tag = await self.repos.tags.get_by_name(workspace_id, tag_name)
        if tag is None:
            return []
        links = await self.repos.asset_tags.list_for_tag(tag.id)
        return await self.repos.assets.get_many([link.asset_id for link in links])

    async def search_by_metadata(self, workspace_id: str, filters: dict) -> list[CollaborationAssetModel]:
        """Naive in-memory metadata filter — sufficient given assets
        are workspace-scoped and expected to number in the hundreds,
        not the exact query pattern a dedicated document store would
        need to serve at larger scale."""
        candidates = await self.repos.assets.list_for_workspace(workspace_id)
        matches = []
        for asset in candidates:
            if all(asset.asset_metadata.get(key) == value for key, value in filters.items()):
                matches.append(asset)
        return matches
