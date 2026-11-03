"""Context Assembly Engine output shapes — kept separate from
`retrieval.schemas.RetrievalResult` because context assembly answers a
different question ("what goes into the prompt, with what citation and
at what token cost") than retrieval does ("what's relevant")."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Citation:
    source_type: str
    source_id: str
    title: str | None
    score: float
    truncated: bool = False


@dataclass
class AssembledContext:
    text: str
    citations: list[Citation] = field(default_factory=list)
    total_tokens: int = 0
    items_included: int = 0
    items_excluded: int = 0
    duplicates_removed: int = 0
    conflicts_resolved: int = 0
    was_summarized: bool = False
