"""RetrievalService — the advanced retrieval engine every AI subsystem
queries memory/knowledge through: semantic, keyword, and hybrid search;
metadata/context/agent/user/project/time-aware filtering; multi-stage
retrieval (broad candidate generation -> scope/metadata filtering ->
re-ranking -> top-K selection); query expansion; and a lightweight
snippet-level context compression for search-result previews (the
heavier, token-budgeted compression used when assembling a full prompt
context lives in the Context Assembly Engine, which builds on this
service rather than duplicating it).
"""
from __future__ import annotations

import time
from datetime import datetime

from memory_platform.config.settings import Settings, get_settings
from memory_platform.core.exceptions import ValidationError
from memory_platform.core.time_utils import as_aware_utc
from memory_platform.domain.enums import SearchMode
from memory_platform.models.knowledge import KnowledgeItemModel
from memory_platform.models.memory_entry import MemoryEntryModel
from memory_platform.reranking.reranker import rerank as rerank_results
from memory_platform.reranking.reranker import top_k as select_top_k
from memory_platform.retrieval.query_expansion import expand_query
from memory_platform.retrieval.schemas import RetrievalResult
from memory_platform.repositories.registry import RepositoryRegistry
from memory_platform.vector_store.vector_platform_service import VectorPlatformService
from memory_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _memory_entry_to_result(model: MemoryEntryModel, *, score: float, match_types: list[str]) -> RetrievalResult:
    return RetrievalResult(
        id=model.id, source_type="memory_entry", content=model.content, title=model.title, score=score,
        importance_score=model.importance_score, created_at=model.created_at, last_accessed_at=model.last_accessed_at,
        metadata={"memory_type": model.memory_type, "scope_type": model.scope_type, "scope_id": model.scope_id, "tags": model.tags},
        match_types=match_types,
    )


def _knowledge_item_to_result(model: KnowledgeItemModel, *, score: float, match_types: list[str]) -> RetrievalResult:
    return RetrievalResult(
        id=model.id, source_type="knowledge_item", content=model.content, title=model.title, score=score,
        importance_score=0.6, created_at=model.created_at, last_accessed_at=None,
        metadata={"category": model.category, "tags": model.tags, "status": model.status},
        match_types=match_types,
    )


class RetrievalService:
    def __init__(self, repos: RepositoryRegistry, *, vector_platform: VectorPlatformService | None = None, ai_core=None, settings: Settings | None = None):
        self.repos = repos
        self.vector_platform = vector_platform
        self.ai_core = ai_core
        self.settings = settings or get_settings()

    # -- keyword search -----------------------------------------------------------------

    async def keyword_search(self, workspace_id: str, query: str, *, memory_type: str | None = None, limit: int = 50) -> list[RetrievalResult]:
        entries = await self.repos.memory_entries.search_keyword(workspace_id, query, memory_type=memory_type, limit=limit)
        return [_memory_entry_to_result(e, score=1.0, match_types=["keyword"]) for e in entries]

    # -- semantic search ------------------------------------------------------------------

    async def semantic_search(self, workspace_id: str, query: str, *, source_type: str = "memory_entry", top_k: int = 10, filter_metadata: dict | None = None) -> list[RetrievalResult]:
        if self.vector_platform is None:
            raise ValidationError("semantic_search requires a configured VectorPlatformService")
        merged_filter = {**(filter_metadata or {}), "source_type": source_type}
        matches = await self.vector_platform.similarity_search_query(query, top_k=top_k, filter_metadata=merged_filter)
        if not matches:
            return []
        ids = [m.id for m in matches]
        if source_type == "memory_entry":
            models = {m.id: m for m in await self.repos.memory_entries.get_many(ids)}
            return [_memory_entry_to_result(models[m.id], score=m.score, match_types=["semantic"]) for m in matches if m.id in models]
        if source_type == "knowledge_item":
            models = {m.id: m for m in await self.repos.knowledge_items.get_many(ids)}
            return [_knowledge_item_to_result(models[m.id], score=m.score, match_types=["semantic"]) for m in matches if m.id in models]
        raise ValidationError(f"unsupported source_type for semantic_search: '{source_type}'")

    # -- hybrid search --------------------------------------------------------------------

    async def hybrid_search(self, workspace_id: str, query: str, *, memory_type: str | None = None, top_k: int = 10, semantic_weight: float | None = None) -> list[RetrievalResult]:
        weight = semantic_weight if semantic_weight is not None else self.settings.hybrid_search_semantic_weight
        keyword_results = await self.keyword_search(workspace_id, query, memory_type=memory_type, limit=top_k * 3)
        semantic_results: list[RetrievalResult] = []
        if self.vector_platform is not None:
            try:
                semantic_results = await self.semantic_search(workspace_id, query, top_k=top_k * 3)
            except ValidationError:
                semantic_results = []

        merged: dict[str, RetrievalResult] = {}
        max_semantic = max((r.score for r in semantic_results), default=1.0) or 1.0
        for r in semantic_results:
            r.score = weight * (r.score / max_semantic)
            merged[r.id] = r
        for r in keyword_results:
            keyword_contribution = (1 - weight) * 1.0
            if r.id in merged:
                merged[r.id].score += keyword_contribution
                merged[r.id].match_types.append("keyword")
            else:
                r.score = keyword_contribution
                merged[r.id] = r

        results = sorted(merged.values(), key=lambda r: r.score, reverse=True)
        return select_top_k(results, top_k)

    # -- context / agent / user / project-aware search (scope-filtered) -------------------

    async def search_for_scope(
        self, workspace_id: str, scope_type: str, scope_id: str, query: str, *, mode: SearchMode = SearchMode.HYBRID, memory_type: str | None = None, top_k: int = 10,
    ) -> list[RetrievalResult]:
        """The shared implementation behind agent/user/project/context-aware
        search — those are just this operation with `scope_type` fixed to
        a particular `ScopeType` value."""
        if mode == SearchMode.KEYWORD:
            candidates = await self.keyword_search(workspace_id, query, memory_type=memory_type, limit=top_k * 3)
        elif mode == SearchMode.SEMANTIC:
            candidates = await self.semantic_search(workspace_id, query, top_k=top_k * 3)
        else:
            candidates = await self.hybrid_search(workspace_id, query, memory_type=memory_type, top_k=top_k * 3)

        scoped = [r for r in candidates if r.metadata.get("scope_type") == scope_type and r.metadata.get("scope_id") == scope_id]
        return select_top_k(scoped, top_k)

    async def agent_aware_search(self, workspace_id: str, agent_id: str, query: str, **kwargs) -> list[RetrievalResult]:
        return await self.search_for_scope(workspace_id, "agent", agent_id, query, **kwargs)

    async def user_aware_search(self, workspace_id: str, user_id: str, query: str, **kwargs) -> list[RetrievalResult]:
        return await self.search_for_scope(workspace_id, "user", user_id, query, **kwargs)

    async def project_aware_search(self, workspace_id: str, project_id: str, query: str, **kwargs) -> list[RetrievalResult]:
        return await self.search_for_scope(workspace_id, "project", project_id, query, **kwargs)

    # -- time-aware search ------------------------------------------------------------------

    async def time_aware_search(
        self, workspace_id: str, query: str, *, start: datetime, end: datetime, mode: SearchMode = SearchMode.HYBRID, memory_type: str | None = None, top_k: int = 10,
    ) -> list[RetrievalResult]:
        if mode == SearchMode.KEYWORD:
            candidates = await self.keyword_search(workspace_id, query, memory_type=memory_type, limit=top_k * 5)
        elif mode == SearchMode.SEMANTIC:
            candidates = await self.semantic_search(workspace_id, query, top_k=top_k * 5)
        else:
            candidates = await self.hybrid_search(workspace_id, query, memory_type=memory_type, top_k=top_k * 5)
        in_range = [r for r in candidates if r.created_at is not None and start <= as_aware_utc(r.created_at) <= end]
        return select_top_k(in_range, top_k)

    # -- multi-stage retrieval --------------------------------------------------------------

    async def multi_stage_retrieve(
        self, workspace_id: str, query: str, *, scope_type: str | None = None, scope_id: str | None = None, memory_type: str | None = None,
        top_k: int = 10, use_query_expansion: bool = False, apply_reranking: bool = True, requested_by: str | None = None, log_retrieval: bool = True,
    ) -> list[RetrievalResult]:
        """Stage 1: (optional) query expansion. Stage 2: broad candidate
        generation via hybrid search, over-fetched. Stage 3: scope
        filtering. Stage 4: re-ranking. Stage 5: top-K selection. Every
        call logs one `RetrievalLogModel` row (the same "shared choke
        point" pattern the Prompt Platform's observability used) so
        latency/quality/failure-rate analytics have real data to work
        from — this is the highest-level retrieval entry point, used
        directly and by the Context Assembly Engine."""
        started = time.perf_counter()
        try:
            queries = [query]
            if use_query_expansion:
                if self.ai_core is None:
                    raise ValidationError("use_query_expansion=True requires an AICoreContext")
                queries += await expand_query(self.ai_core, query)

            candidate_pool: dict[str, RetrievalResult] = {}
            for q in queries:
                for r in await self.hybrid_search(workspace_id, q, memory_type=memory_type, top_k=top_k * 3):
                    if r.id in candidate_pool:
                        candidate_pool[r.id].score = max(candidate_pool[r.id].score, r.score)
                    else:
                        candidate_pool[r.id] = r
            candidates = list(candidate_pool.values())

            if scope_type is not None and scope_id is not None:
                candidates = [r for r in candidates if r.metadata.get("scope_type") == scope_type and r.metadata.get("scope_id") == scope_id]

            if apply_reranking:
                candidates = rerank_results(candidates)
            else:
                candidates.sort(key=lambda r: r.score, reverse=True)

            results = select_top_k(candidates, top_k)
        except Exception as exc:  # noqa: BLE001
            if log_retrieval:
                await self._log_retrieval(workspace_id, query, scope_type=scope_type, scope_id=scope_id, top_k=top_k, result_count=0,
                                           latency_ms=(time.perf_counter() - started) * 1000, requested_by=requested_by, success=False, error_message=str(exc))
            raise
        else:
            if log_retrieval:
                await self._log_retrieval(workspace_id, query, scope_type=scope_type, scope_id=scope_id, top_k=top_k, result_count=len(results),
                                           latency_ms=(time.perf_counter() - started) * 1000, requested_by=requested_by, success=True, error_message=None)
            return results

    async def _log_retrieval(
        self, workspace_id: str, query: str, *, scope_type: str | None, scope_id: str | None, top_k: int, result_count: int,
        latency_ms: float, requested_by: str | None, success: bool, error_message: str | None,
    ) -> None:
        from memory_platform.database.base import new_uuid
        from memory_platform.models.observability import RetrievalLogModel

        await self.repos.retrieval_logs.add(RetrievalLogModel(
            id=new_uuid(), workspace_id=workspace_id, query_text=query, search_mode=SearchMode.HYBRID.value,
            scope_filters={"scope_type": scope_type, "scope_id": scope_id}, top_k=top_k, result_count=result_count,
            latency_ms=latency_ms, requested_by=requested_by, success=success, error_message=error_message,
        ))

    # -- context compression (lightweight, snippet-level) ------------------------------------

    @staticmethod
    def compress_content(text: str, *, max_chars: int = 300) -> str:
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars].rsplit(" ", 1)[0]
        return truncated + "…"
