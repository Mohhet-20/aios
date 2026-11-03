"""HallucinationDetectionService: runs a `GroundingVerifier` over a
claim against its source context, validates any `[n]`-style citations
against the context list, optionally scores cross-generation
consistency when repeated samples of the same claim are supplied, and
persists the result as a `HallucinationCheckModel`. Callable standalone
(`subject_type="adhoc"`) — e.g. from Observability against a live
production response — or wired into an evaluation item's scoring."""
from __future__ import annotations

import re

from eval_platform.config.settings import get_settings
from eval_platform.core.exceptions import HallucinationCheckError
from eval_platform.hallucination.verifier import GroundingVerifier, LexicalOverlapVerifier, VerificationOutcome, _tokens
from eval_platform.models.hallucination import HallucinationCheckModel
from eval_platform.repositories.registry import RepositoryRegistry

_CITATION_RE = re.compile(r"\[(\d+)\]")
_DEFAULT_VERIFIER = LexicalOverlapVerifier()


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class HallucinationDetectionService:
    def __init__(self, repos: RepositoryRegistry, *, verifier: GroundingVerifier | None = None):
        self.repos = repos
        self.verifier = verifier or _DEFAULT_VERIFIER

    async def run_check(
        self, workspace_id: str, *, claim_text: str, source_context: list[str], subject_type: str,
        subject_id: str | None = None, repeated_claims: list[str] | None = None,
    ) -> HallucinationCheckModel:
        if not claim_text or not claim_text.strip():
            raise HallucinationCheckError("cannot run a hallucination check against empty claim_text")
        if not source_context:
            raise HallucinationCheckError("cannot run a hallucination check without source_context")

        outcome = await self.verifier.verify(claim_text, source_context)
        citations_checked = self._check_citations(claim_text, source_context)
        consistency_score = self._consistency(claim_text, repeated_claims) if repeated_claims else None
        confidence = self._confidence(outcome)

        threshold = get_settings().hallucination_groundedness_threshold
        grounded = outcome.groundedness_score >= threshold

        return await self.repos.hallucination_checks.add(HallucinationCheckModel(
            workspace_id=workspace_id, subject_type=subject_type, subject_id=subject_id,
            source_context="\n".join(source_context), claim_text=claim_text, grounded=grounded,
            groundedness_score=outcome.groundedness_score, confidence=confidence,
            unsupported_claims=outcome.unsupported_claims, citations_checked=citations_checked,
            consistency_score=consistency_score, method=self.verifier.method,
        ))

    async def list_for_subject(self, subject_type: str, subject_id: str) -> list[HallucinationCheckModel]:
        return await self.repos.hallucination_checks.list_for_subject(subject_type, subject_id)

    def _check_citations(self, claim_text: str, source_context: list[str]) -> list[dict]:
        citations = _CITATION_RE.findall(claim_text)
        return [{"index": int(c), "valid": 1 <= int(c) <= len(source_context)} for c in citations]

    def _consistency(self, claim_text: str, repeated_claims: list[str]) -> float:
        token_sets = [_tokens(c) for c in (claim_text, *repeated_claims)]
        pairs = [(a, b) for i, a in enumerate(token_sets) for b in token_sets[i + 1:]]
        if not pairs:
            return 1.0
        return sum(_jaccard(a, b) for a, b in pairs) / len(pairs)

    def _confidence(self, outcome: VerificationOutcome) -> float:
        """The fraction of the claim's sentences that actually carried
        enough content to be scored — an honest measure of how much
        signal the groundedness score is based on, not a fabricated
        certainty number. A claim that's mostly unscorable filler earns
        low confidence even if the few scorable sentences were grounded."""
        if not outcome.sentence_verdicts:
            return 0.0
        scorable = sum(1 for v in outcome.sentence_verdicts if v.scorable)
        return scorable / len(outcome.sentence_verdicts)
