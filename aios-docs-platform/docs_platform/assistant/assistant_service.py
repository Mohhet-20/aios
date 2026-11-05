"""AI Documentation Assistant. This is explicitly a retrieval-and-
extract assistant, not an LLM-backed one — it ranks published pages
and KB articles by keyword overlap against the question
(`retrieval_rules.rank_candidates`) and returns an extractive summary
of the best match as its "answer", with a confidence score equal to
that match's overlap score. Below `assistant_confidence_threshold` it
honestly reports "no confident answer" rather than fabricating one.
Wiring this to a real LLM later is a drop-in replacement for
`_synthesize_answer` — the retrieval/ranking and session-recording
plumbing around it doesn't change."""
from __future__ import annotations

from datetime import timedelta, timezone

from docs_platform.assistant.retrieval_rules import extractive_summary, rank_candidates
from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import AssistantSessionNotFoundError
from docs_platform.models.assistant import AssistantSessionModel
from docs_platform.models.documentation import DocPageModel
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.clock import utc_now


class AssistantService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def _candidate_pool(self, tenant_id: str) -> dict[str, tuple[str, str]]:
        """Maps a doc ref -> (title, searchable text) for everything
        currently eligible to be surfaced as an answer: published
        pages and published KB articles. Draft/archived/deprecated
        content is deliberately excluded — the assistant should never
        cite something a reader can't actually navigate to."""
        pool: dict[str, tuple[str, str]] = {}
        for page in await self.repos.doc_pages.list_for_tenant(tenant_id, status="published"):
            pool[f"page:{page.id}"] = (page.title, f"{page.title} {page.content}")
        for article in await self.repos.kb_articles.list_for_tenant(tenant_id, status="published"):
            pool[f"kb:{article.id}"] = (article.title, f"{article.title} {article.content}")
        return pool

    async def ask(self, tenant_id: str, question: str, *, user_id: str | None = None) -> AssistantSessionModel:
        pool = await self._candidate_pool(tenant_id)
        ranked = rank_candidates(question, [(ref, text) for ref, (_, text) in pool.items()])

        answer: str | None = None
        confidence: float | None = None
        related_refs = [ref for ref, _ in ranked]

        if ranked and ranked[0][1] >= self.settings.assistant_confidence_threshold:
            top_ref, confidence = ranked[0]
            _, top_text = pool[top_ref]
            answer = extractive_summary(top_text)

        session = AssistantSessionModel(
            tenant_id=tenant_id, user_id=user_id, question=question, answer=answer,
            related_doc_refs=related_refs, confidence=confidence,
        )
        return await self.repos.assistant_sessions.add(session)

    async def get_or_404(self, tenant_id: str, session_id: str) -> AssistantSessionModel:
        session = await self.repos.assistant_sessions.get_or_404(session_id)
        if session.tenant_id != tenant_id:
            raise AssistantSessionNotFoundError(f"Assistant session '{session_id}' not found for tenant '{tenant_id}'")
        return session

    async def suggest_related(self, tenant_id: str, doc_ref: str, *, limit: int = 5) -> list[tuple[str, float]]:
        pool = await self._candidate_pool(tenant_id)
        if doc_ref not in pool:
            return []
        _, source_text = pool[doc_ref]
        others = [(ref, text) for ref, (_, text) in pool.items() if ref != doc_ref]
        return rank_candidates(source_text, others, limit=limit)

    async def find_troubleshooting(self, tenant_id: str, query: str, *, limit: int = 5) -> list[tuple[str, float]]:
        articles = await self.repos.kb_articles.list_for_tenant(tenant_id, article_type="troubleshooting", status="published")
        candidates = [(f"kb:{a.id}", f"{a.title} {a.content}") for a in articles]
        return rank_candidates(query, candidates, limit=limit)

    def summarize(self, text: str, *, max_sentences: int = 3) -> str:
        return extractive_summary(text, max_sentences=max_sentences)

    async def detect_outdated_pages(self, tenant_id: str) -> list[DocPageModel]:
        """A page is "outdated" if it's published but hasn't been
        reviewed within `doc_staleness_days` — or was never reviewed
        at all, which is the more urgent case."""
        cutoff = utc_now() - timedelta(days=self.settings.doc_staleness_days)
        published = await self.repos.doc_pages.list_for_tenant(tenant_id, status="published")
        outdated = []
        for page in published:
            reviewed_at = page.last_reviewed_at
            if reviewed_at is None:
                outdated.append(page)
                continue
            # SQLite round-trips DateTime(timezone=True) columns as
            # naive — normalize to aware (assuming UTC, the only
            # timezone this platform ever writes) before comparing,
            # the same pitfall documented across every other AIOS
            # platform's naive/aware datetime comparisons.
            if reviewed_at.tzinfo is None:
                reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
            if reviewed_at < cutoff:
                outdated.append(page)
        return outdated

    def generate_code_example(self, sdk_language: str, operation_ref: str) -> str:
        """A templated, disclosed-simple code example — not real code
        generation against a live SDK. Useful as a starting-point
        skeleton for a human (or the SDK doc generation job) to fill
        in against the actual client library."""
        templates = {
            "python": f'client.{operation_ref}(...)  # see SDK docs for parameters',
            "typescript": f'await client.{operation_ref}({{ /* params */ }});',
            "cli": f'aios {operation_ref.replace(".", " ")} --help',
        }
        return templates.get(sdk_language, f"# example for '{operation_ref}' on {sdk_language} — see SDK reference")

    async def list_sessions(self, tenant_id: str, *, user_id: str | None = None, limit: int = 50) -> list[AssistantSessionModel]:
        if user_id:
            return await self.repos.assistant_sessions.list_for_user(tenant_id, user_id, limit=limit)
        return await self.repos.assistant_sessions.list_recent(tenant_id, limit=limit)
