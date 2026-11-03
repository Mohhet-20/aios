"""Pure keyword-overlap retrieval scoring — no DB/service imports.
This is a disclosed simplification, not a real embedding-based
semantic search: it tokenizes on whitespace/punctuation, lowercases,
and scores a candidate by what fraction of the query's tokens appear
in it (a directional containment score, not symmetric Jaccard,
since a short query matching entirely inside a long document should
score as a strong match even though the document has plenty of
tokens the query doesn't mention)."""
from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def score_match(query: str, text: str) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0
    text_tokens = tokenize(text)
    overlap = query_tokens & text_tokens
    return len(overlap) / len(query_tokens)


def rank_candidates(query: str, candidates: list[tuple[str, str]], *, limit: int = 5) -> list[tuple[str, float]]:
    """`candidates` is a list of (ref, text) pairs. Returns (ref,
    score) pairs sorted by descending score, ties broken by original
    order, truncated to `limit`."""
    scored = [(ref, score_match(query, text)) for ref, text in candidates]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [pair for pair in scored if pair[1] > 0][:limit]


def extractive_summary(text: str, *, max_sentences: int = 3) -> str:
    """A disclosed-simple extractive summary: the first `max_sentences`
    sentences, not a real abstractive summarizer. Splits on
    '.'/'!'/'?' followed by whitespace."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(s for s in sentences[:max_sentences] if s)
