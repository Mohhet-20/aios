"""Enterprise Search: keyword/full-text search across published pages
and KB articles (`retrieval_rules.rank_candidates` — the same
overlap-scoring approach the AI assistant uses, since both are
answering "what's relevant to this text" over the same content pool),
with every query logged for popularity/failed-search analytics and an
optional doc-type/article-type filter.

`assistant_service.AssistantService` and this service intentionally
don't import each other despite the shared retrieval approach — each
is a legitimate standalone entry point (search results power the
search console; the assistant's "related documentation" powers a
different UI), and keeping them decoupled avoids a needless
cross-module dependency for what's a handful of shared lines."""
from __future__ import annotations

from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import InvalidSearchQueryError
from docs_platform.models.search import SearchQueryLogModel
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.search.popularity_rules import top_queries
from docs_platform.assistant.retrieval_rules import rank_candidates


class SearchService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def _candidate_pool(self, tenant_id: str, *, doc_type: str | None = None) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        for page in await self.repos.doc_pages.list_for_tenant(tenant_id, doc_type=doc_type, status="published"):
            candidates.append((f"page:{page.id}", f"{page.title} {page.content}"))
        if doc_type is None:
            for article in await self.repos.kb_articles.list_for_tenant(tenant_id, status="published"):
                candidates.append((f"kb:{article.id}", f"{article.title} {article.content}"))
        return candidates

    async def search(self, tenant_id: str, query: str, *, doc_type: str | None = None, limit: int | None = None) -> list[tuple[str, float]]:
        if len(query.strip()) < self.settings.search_min_query_length:
            raise InvalidSearchQueryError(f"Search query must be at least {self.settings.search_min_query_length} characters")

        candidates = await self._candidate_pool(tenant_id, doc_type=doc_type)
        results = rank_candidates(query, candidates, limit=limit or self.settings.search_result_limit_default)

        await self.repos.search_query_logs.add(SearchQueryLogModel(tenant_id=tenant_id, query=query, result_count=len(results)))
        return results

    async def record_click(self, tenant_id: str, query_log_id: str, doc_ref: str) -> SearchQueryLogModel:
        log = await self.repos.search_query_logs.get_or_404(query_log_id)
        log.clicked_doc_ref = doc_ref
        return await self.repos.search_query_logs.update(log)

    async def recent_queries(self, tenant_id: str, *, limit: int = 20) -> list[SearchQueryLogModel]:
        return await self.repos.search_query_logs.list_recent(tenant_id, limit=limit)

    async def failed_searches(self, tenant_id: str, *, limit: int = 20) -> list[SearchQueryLogModel]:
        return await self.repos.search_query_logs.list_failed(tenant_id, limit=limit)

    async def popular_queries(self, tenant_id: str, *, limit: int = 10, sample_size: int = 500) -> list[tuple[str, int]]:
        logs = await self.repos.search_query_logs.list_recent(tenant_id, limit=sample_size)
        return top_queries([log.query for log in logs], limit=limit)
