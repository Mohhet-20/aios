"""ToolDiscoveryService: every way an AI agent or a human building a
workflow finds the right tool — capability/category/tag/version search,
a lexical "semantic" search over name/description/capabilities (the
same term-overlap approach `connectors/web_search.py` uses for the same
reason: real, deterministic ranking without a vector index dependency
this platform doesn't own — swap in real embedding similarity later
behind the same method signature), recently-used (derived from
execution history, never a separately-maintained cache), favorites, and
a simple, explainable recommendation heuristic (same category as what
you've used recently, weighted by workspace-wide popularity)."""
from __future__ import annotations

from collections import Counter

from tool_platform.models.discovery import ToolFavoriteModel
from tool_platform.models.tool import ToolModel
from tool_platform.repositories.registry import RepositoryRegistry


def _lexical_score(query: str, text: str) -> float:
    q_terms = set(query.lower().split())
    t_terms = set(text.lower().split())
    if not q_terms or not t_terms:
        return 0.0
    return len(q_terms & t_terms) / len(q_terms)


class ToolDiscoveryService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def search_by_category(self, workspace_id: str, category: str) -> list[ToolModel]:
        return await self.repos.tools.list_for_workspace(workspace_id, category=category)

    async def search_by_tag(self, workspace_id: str, tag: str) -> list[ToolModel]:
        return await self.repos.tools.search_by_tag(workspace_id, tag)

    async def search_by_capability(self, workspace_id: str, capability: str) -> list[ToolModel]:
        tools = await self.repos.tools.list_for_workspace(workspace_id, status="published")
        matches = []
        for tool in tools:
            if not tool.current_version_id:
                continue
            version = await self.repos.tool_versions.get_or_404(tool.current_version_id)
            if capability in (version.capabilities or []):
                matches.append(tool)
        return matches

    async def semantic_search(self, workspace_id: str, query: str, *, top_k: int = 10) -> list[ToolModel]:
        tools = await self.repos.tools.list_for_workspace(workspace_id, status="published")
        scored = []
        for tool in tools:
            haystack = " ".join([tool.name, tool.description or "", " ".join(tool.tags or [])])
            score = _lexical_score(query, haystack)
            if score > 0:
                scored.append((score, tool))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [tool for _score, tool in scored[:top_k]]

    async def recently_used(self, user_id: str, *, limit: int = 10) -> list[ToolModel]:
        executions = await self.repos.executions.list_for_user(user_id, limit=100)
        seen: list[str] = []
        for execution in executions:
            if execution.tool_id not in seen:
                seen.append(execution.tool_id)
            if len(seen) >= limit:
                break
        return await self.repos.tools.get_many(seen)

    # -- favorites ------------------------------------------------------------------

    async def add_favorite(self, tool_id: str, user_id: str) -> ToolFavoriteModel:
        existing = await self.repos.tool_favorites.get_favorite(tool_id, user_id)
        if existing is not None:
            return existing
        return await self.repos.tool_favorites.add(ToolFavoriteModel(tool_id=tool_id, user_id=user_id))

    async def remove_favorite(self, tool_id: str, user_id: str) -> None:
        existing = await self.repos.tool_favorites.get_favorite(tool_id, user_id)
        if existing is not None:
            await self.repos.tool_favorites.delete(existing, hard=True)

    async def list_favorites(self, user_id: str) -> list[ToolModel]:
        favorites = await self.repos.tool_favorites.list_for_user(user_id)
        return await self.repos.tools.get_many([fav.tool_id for fav in favorites])

    # -- recommendations --------------------------------------------------------------

    async def recommend(self, workspace_id: str, user_id: str, *, limit: int = 5) -> list[ToolModel]:
        """Heuristic: rank not-yet-favorited published tools by (1) whether
        their category matches one of the user's 5 most recently-used
        tools' categories, then (2) overall execution count in this
        workspace (a real popularity signal, not synthesized)."""
        recent = await self.recently_used(user_id, limit=5)
        recent_categories = {t.category for t in recent}
        favorited_ids = {t.id for t in await self.list_favorites(user_id)}

        candidates = await self.repos.tools.list_for_workspace(workspace_id, status="published")
        candidates = [t for t in candidates if t.id not in favorited_ids]

        all_executions = await self.repos.executions.list_for_workspace(workspace_id, limit=10_000)
        popularity = Counter(e.tool_id for e in all_executions)

        def _rank_key(tool: ToolModel) -> tuple:
            category_match = 1 if tool.category in recent_categories else 0
            return (category_match, popularity.get(tool.id, 0))

        ranked = sorted(candidates, key=_rank_key, reverse=True)
        return ranked[:limit]
