"""ContextAssemblyService — the intelligent context pipeline every agent/
workflow prompt gets built from: memory selection + retrieval ranking
(delegates to `RetrievalService.multi_stage_retrieve`, which already does
hybrid search, scope filtering, and re-ranking), duplicate removal,
lightweight conflict resolution, real token-budget management (via the
AI Core's tokenizer), source attribution and citation metadata, and
prompt assembly into a ready-to-send text block. Falls back to LLM-backed
summarization only when the budget can't be met by truncation alone.
"""
from __future__ import annotations

import hashlib
import re
import time

from ai_core.bootstrap import AICoreContext
from ai_core.tokenizer.counter import count_tokens

from memory_platform.config.settings import Settings, get_settings
from memory_platform.context_engine.compression import summarize_context
from memory_platform.context_engine.schemas import AssembledContext, Citation
from memory_platform.retrieval.retrieval_service import RetrievalService
from memory_platform.retrieval.schemas import RetrievalResult


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _content_fingerprint(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()


def label_for(result: RetrievalResult) -> str:
    return result.title or f"{result.source_type}:{result.id[:8]}"


def _jaccard_similarity(a: str, b: str) -> float:
    tokens_a, tokens_b = set(_normalize(a).split()), set(_normalize(b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


class ContextAssemblyService:
    def __init__(self, retrieval_service: RetrievalService, *, ai_core: AICoreContext | None = None, settings: Settings | None = None):
        self.retrieval_service = retrieval_service
        self.ai_core = ai_core
        self.settings = settings or get_settings()

    # -- duplicate removal -------------------------------------------------------------

    @staticmethod
    def _remove_duplicates(results: list[RetrievalResult], *, near_duplicate_threshold: float = 0.9) -> tuple[list[RetrievalResult], int]:
        kept: list[RetrievalResult] = []
        seen_fingerprints: set[str] = set()
        removed = 0
        for r in results:
            fp = _content_fingerprint(r.content)
            if fp in seen_fingerprints:
                removed += 1
                continue
            is_near_duplicate = any(_jaccard_similarity(r.content, k.content) >= near_duplicate_threshold for k in kept)
            if is_near_duplicate:
                removed += 1
                continue
            seen_fingerprints.add(fp)
            kept.append(r)
        return kept, removed

    # -- conflict resolution -----------------------------------------------------------

    @staticmethod
    def _resolve_conflicts(results: list[RetrievalResult]) -> tuple[list[RetrievalResult], int]:
        """Memory-layer supersession (`MemoryService.supersede`) already
        keeps superseded entries out of ACTIVE retrieval results, so most
        conflicts never reach this stage. This is the second-layer check:
        when two candidates share the same non-null title (the same named
        fact, recorded twice), keep only the highest-scoring one rather
        than presenting the model with two different answers to "what is
        X" side by side."""
        best_by_title: dict[str, RetrievalResult] = {}
        untitled: list[RetrievalResult] = []
        conflicts = 0
        for r in results:
            if not r.title:
                untitled.append(r)
                continue
            key = _normalize(r.title)
            if key in best_by_title:
                conflicts += 1
                if r.score > best_by_title[key].score:
                    best_by_title[key] = r
            else:
                best_by_title[key] = r
        resolved = list(best_by_title.values()) + untitled
        resolved.sort(key=lambda r: r.score, reverse=True)
        return resolved, conflicts

    # -- token budget management + assembly --------------------------------------------

    async def assemble_context(
        self, workspace_id: str, query: str, *, scope_type: str | None = None, scope_id: str | None = None, memory_type: str | None = None,
        candidate_pool_size: int = 20, token_budget: int | None = None, use_query_expansion: bool = False,
        allow_llm_summarization: bool = True, per_item_max_chars: int = 1200, requested_by: str | None = None, log_assembly: bool = True,
    ) -> AssembledContext:
        started = time.perf_counter()
        budget = token_budget if token_budget is not None else self.settings.context_token_budget

        # Stage 1-2: memory selection + retrieval ranking (multi-stage retrieve already re-ranks)
        candidates = await self.retrieval_service.multi_stage_retrieve(
            workspace_id, query, scope_type=scope_type, scope_id=scope_id, memory_type=memory_type,
            top_k=candidate_pool_size, use_query_expansion=use_query_expansion, apply_reranking=True,
        )

        # Stage 3: duplicate removal
        deduped, duplicates_removed = self._remove_duplicates(candidates)

        # Stage 4: conflict resolution
        resolved, conflicts_resolved = self._resolve_conflicts(deduped)

        # Stage 5: per-item compression (snippet-level truncation) and total-size check
        snippets = [(r, self.retrieval_service.compress_content(r.content, max_chars=per_item_max_chars)) for r in resolved]
        snippet_tokens = [count_tokens(content) for _, content in snippets]
        total_untruncated_tokens = sum(snippet_tokens)

        was_summarized = False
        if total_untruncated_tokens > budget and allow_llm_summarization and self.ai_core is not None and snippets:
            # Stage 6a: whole-context LLM summarization — preferred over
            # truncating individual items when the model is available,
            # since it preserves meaning from every source rather than
            # cutting some off mid-sentence.
            combined = "\n\n".join(f"[{i + 1}] {label_for(r)}\n{content}" for i, (r, content) in enumerate(snippets))
            summary = await summarize_context(self.ai_core, combined, max_summary_tokens=budget)
            text = summary
            was_summarized = True
            used_tokens = count_tokens(summary)
            citations = [Citation(source_type=r.source_type, source_id=r.id, title=r.title, score=r.score, truncated=False) for r, _ in snippets]
            items_included, items_excluded = len(snippets), 0
        else:
            # Stage 6b: greedy token-budget selection with a final
            # further-truncated fragment when nothing more whole fits.
            included: list[tuple[RetrievalResult, str, bool]] = []
            excluded_count = 0
            used_tokens = 0
            for r, content in snippets:
                truncated = content != r.content
                item_tokens = count_tokens(content)
                if used_tokens + item_tokens > budget:
                    remaining = budget - used_tokens
                    if remaining > 20:  # worth including a further-truncated fragment
                        words = content.split()
                        fragment = ""
                        for w in words:
                            candidate_fragment = f"{fragment} {w}".strip()
                            if count_tokens(candidate_fragment) > remaining:
                                break
                            fragment = candidate_fragment
                        if fragment:
                            included.append((r, fragment + "…", True))
                            used_tokens += count_tokens(fragment)
                    excluded_count += 1
                    continue
                included.append((r, content, truncated))
                used_tokens += item_tokens

            text = self._assemble_prompt_text(included)
            citations = [Citation(source_type=r.source_type, source_id=r.id, title=r.title, score=r.score, truncated=truncated) for r, _, truncated in included]
            items_included, items_excluded = len(included), excluded_count

        result = AssembledContext(
            text=text, citations=citations, total_tokens=used_tokens, items_included=items_included, items_excluded=items_excluded,
            duplicates_removed=duplicates_removed, conflicts_resolved=conflicts_resolved, was_summarized=was_summarized,
        )
        if log_assembly:
            await self._log_assembly(workspace_id, query, token_budget=budget, tokens_used=used_tokens, citations=citations,
                                      compression_applied=was_summarized, latency_ms=(time.perf_counter() - started) * 1000, requested_by=requested_by)
        return result

    async def _log_assembly(
        self, workspace_id: str, query: str, *, token_budget: int, tokens_used: int, citations: list[Citation],
        compression_applied: bool, latency_ms: float, requested_by: str | None,
    ) -> None:
        from memory_platform.database.base import new_uuid
        from memory_platform.models.observability import ContextAssemblyLogModel

        await self.retrieval_service.repos.context_assembly_logs.add(ContextAssemblyLogModel(
            id=new_uuid(), workspace_id=workspace_id, query_text=query, token_budget=token_budget, tokens_used=tokens_used,
            sources_used=[c.source_type for c in citations], compression_applied=compression_applied, latency_ms=latency_ms, requested_by=requested_by,
        ))

    # -- prompt assembly -----------------------------------------------------------------

    @staticmethod
    def _assemble_prompt_text(included: list[tuple[RetrievalResult, str, bool]]) -> str:
        """Source attribution baked directly into the assembled text —
        every block is numbered and labeled, and the citation list
        returned alongside maps `[n]` back to `(source_type, source_id)`."""
        blocks = []
        for i, (r, content, truncated) in enumerate(included):
            label = r.title or f"{r.source_type}:{r.id[:8]}"
            suffix = " (truncated)" if truncated else ""
            blocks.append(f"[{i + 1}] {label}{suffix}\n{content}")
        return "\n\n".join(blocks)
