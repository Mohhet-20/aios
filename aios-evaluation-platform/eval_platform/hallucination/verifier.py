"""GroundingVerifier: the pluggable seam that actually decides whether
a claim is supported by its source context. `LexicalOverlapVerifier` is
the default, real, deterministic implementation — sentence-level
token-overlap, exactly the `method="lexical_overlap"` documented on
`HallucinationCheckModel`. A stronger verifier (an NLI model, an
LLM-as-judge call through AI Core, an external fact-checking API) is a
new class implementing the same Protocol; nothing in
`hallucination/service.py` has to change to use it — the same
swappable, disclosed-gap pattern as every other "genuinely computed
today, upgradeable later" connector in this AIOS build."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str, *, min_len: int = 1) -> set[str]:
    return {t for t in _WORD_RE.findall(text.lower()) if len(t) >= min_len}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


@dataclass
class SentenceVerdict:
    sentence: str
    supported: bool
    overlap_ratio: float
    scorable: bool


@dataclass
class VerificationOutcome:
    groundedness_score: float
    sentence_verdicts: list[SentenceVerdict] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)


@runtime_checkable
class GroundingVerifier(Protocol):
    method: str

    async def verify(self, claim_text: str, source_context: list[str]) -> VerificationOutcome: ...


class LexicalOverlapVerifier:
    """A sentence is "supported" when at least `support_threshold` of
    its content tokens (length >= `min_token_len`, to filter out
    function words) appear in the union of the source context. A
    sentence with no scorable tokens at all (too short / pure filler)
    is marked supported-but-not-scorable rather than penalized or
    fabricated a verdict for — `VerificationOutcome`'s per-sentence
    `scorable` flag is what `HallucinationDetectionService` uses to
    derive an honest confidence score."""

    method = "lexical_overlap"

    def __init__(self, *, support_threshold: float = 0.5, min_token_len: int = 4):
        self.support_threshold = support_threshold
        self.min_token_len = min_token_len

    async def verify(self, claim_text: str, source_context: list[str]) -> VerificationOutcome:
        context_tokens = _tokens(" ".join(source_context), min_len=self.min_token_len)
        sentences = _sentences(claim_text)
        if not sentences:
            return VerificationOutcome(groundedness_score=0.0)

        verdicts: list[SentenceVerdict] = []
        unsupported: list[str] = []
        for sentence in sentences:
            sentence_tokens = _tokens(sentence, min_len=self.min_token_len)
            if not sentence_tokens:
                verdicts.append(SentenceVerdict(sentence=sentence, supported=True, overlap_ratio=1.0, scorable=False))
                continue
            overlap = len(sentence_tokens & context_tokens) / len(sentence_tokens)
            supported = overlap >= self.support_threshold
            verdicts.append(SentenceVerdict(sentence=sentence, supported=supported, overlap_ratio=overlap, scorable=True))
            if not supported:
                unsupported.append(sentence)

        groundedness_score = sum(1 for v in verdicts if v.supported) / len(verdicts)
        return VerificationOutcome(groundedness_score=groundedness_score, sentence_verdicts=verdicts, unsupported_claims=unsupported)
