"""Generic retrieval result container — deliberately decoupled from any
one ORM model (`MemoryEntryModel`, `KnowledgeItemModel`, ...) so search,
re-ranking, and context assembly can all work against one shape
regardless of what kind of thing was retrieved."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RetrievalResult:
    id: str
    source_type: str
    content: str
    score: float
    title: str | None = None
    importance_score: float = 0.5
    created_at: datetime | None = None
    last_accessed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    match_types: list[str] = field(default_factory=list, metadata={"doc": "e.g. ['semantic'], ['keyword'], ['semantic', 'keyword'] for hybrid"})
