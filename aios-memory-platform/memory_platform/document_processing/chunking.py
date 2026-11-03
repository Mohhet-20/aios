"""Intelligent, token-aware chunking: splits on paragraph/sentence
boundaries first (never mid-sentence when avoidable), then packs those
units into chunks up to `max_tokens`, with `overlap_tokens` of trailing
context repeated into the next chunk so retrieval doesn't lose meaning
at a chunk boundary. Token counts use the AI Core's real tokenizer
(`ai_core.tokenizer.counter.count_tokens`), not a char-count proxy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ai_core.tokenizer.counter import count_tokens

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    content: str
    chunk_index: int
    start_offset: int
    end_offset: int
    token_count: int


def _split_units(text: str) -> list[str]:
    """Paragraphs, further split into sentences if a single paragraph
    alone would blow the chunk budget."""
    units: list[str] = []
    for para in _PARAGRAPH_SPLIT.split(text):
        para = para.strip()
        if not para:
            continue
        if count_tokens(para) > 400:
            units.extend(s.strip() for s in _SENTENCE_SPLIT.split(para) if s.strip())
        else:
            units.append(para)
    return units


def chunk_text(text: str, *, max_tokens: int = 400, overlap_tokens: int = 50, provider: str = "openai", model: str = "gpt-4o") -> list[Chunk]:
    if not text or not text.strip():
        return []

    units = _split_units(text)
    if not units:
        return []

    chunks: list[Chunk] = []
    current_units: list[str] = []
    current_tokens = 0
    cursor = 0
    chunk_start = 0

    def _flush(next_cursor: int) -> None:
        nonlocal current_units, current_tokens, chunk_start
        if not current_units:
            return
        content = " ".join(current_units)
        chunks.append(Chunk(
            content=content, chunk_index=len(chunks), start_offset=chunk_start, end_offset=next_cursor,
            token_count=count_tokens(content, provider=provider, model=model),
        ))
        # carry the trailing `overlap_tokens` worth of units into the next chunk
        overlap: list[str] = []
        overlap_count = 0
        for u in reversed(current_units):
            t = count_tokens(u, provider=provider, model=model)
            if overlap_count + t > overlap_tokens:
                break
            overlap.insert(0, u)
            overlap_count += t
        current_units = overlap
        current_tokens = overlap_count
        chunk_start = next_cursor - sum(len(u) + 1 for u in overlap)

    for unit in units:
        unit_tokens = count_tokens(unit, provider=provider, model=model)
        if current_tokens + unit_tokens > max_tokens and current_units:
            _flush(cursor)
        current_units.append(unit)
        current_tokens += unit_tokens
        cursor += len(unit) + 1

    _flush(cursor)
    return chunks
