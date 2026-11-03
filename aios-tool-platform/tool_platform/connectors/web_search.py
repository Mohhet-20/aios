"""WebSearchHandler: a genuine, deterministic term-overlap search over an
in-process document set — real ranking logic, no network dependency on
an actual search engine this platform doesn't own. A production
deployment swaps `documents` for a real provider (Bing/Google/Brave
Search API) behind this same `execute` signature; the connector_key
stays "web_search" either way, so no workflow or tool version needs to
change when that swap happens."""
from __future__ import annotations

from typing import Any

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler


def _score(query: str, text: str) -> float:
    q_terms = set(query.lower().split())
    t_terms = set(text.lower().split())
    if not q_terms or not t_terms:
        return 0.0
    return len(q_terms & t_terms) / len(q_terms)


class WebSearchHandler(ConnectorHandler):
    def __init__(self, documents: list[dict[str, str]] | None = None):
        """`documents`: [{"title": ..., "url": ..., "text": ...}, ...] —
        the reference corpus this connector ranks against. Swap this
        constructor argument for a real provider client in production."""
        self._documents = documents or []

    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        query = ctx.input_data.get("query") or ctx.config.get("query")
        if not query:
            raise ToolExecutionError("web_search tool call requires a 'query'")
        top_k = ctx.input_data.get("top_k", ctx.config.get("top_k", 5))

        documents = ctx.config.get("documents") or self._documents
        scored = sorted(
            ({**d, "score": _score(query, d.get("text", ""))} for d in documents),
            key=lambda d: d["score"], reverse=True,
        )
        results = [d for d in scored if d["score"] > 0][:top_k]
        return {"query": query, "results": results, "result_count": len(results)}
