"""Pure certification scoring/decision logic — no DB/service imports.
`compute_overall_score` renormalizes `certification_score_weights` over
whichever category scores were actually supplied (a certification run
that has no AI-quality signal yet, say, still produces a meaningful
overall score from the remaining categories rather than silently
treating the missing one as zero and dragging the score down for a
reason that has nothing to do with quality)."""
from __future__ import annotations

from quality_platform.domain.enums import CertificationDecision

DEFAULT_CONDITIONAL_BAND_PCT = 10.0


def compute_overall_score(scores: dict[str, float], weights: dict[str, float]) -> float:
    relevant = {category: weight for category, weight in weights.items() if category in scores}
    if not relevant:
        return 0.0
    total_weight = sum(relevant.values())
    return sum(scores[category] * weight for category, weight in relevant.items()) / total_weight


def decide_certification(
    overall_score: float, *, min_score_for_approval: float, conditional_band_pct: float = DEFAULT_CONDITIONAL_BAND_PCT
) -> CertificationDecision:
    """Approved at or above the bar; within `conditional_band_pct`
    points below it, approved with conditions (close enough to ship
    with follow-up tracked, not a clean pass); further below, rejected."""
    if overall_score >= min_score_for_approval:
        return CertificationDecision.APPROVED
    if overall_score >= min_score_for_approval - conditional_band_pct:
        return CertificationDecision.APPROVED_WITH_CONDITIONS
    return CertificationDecision.REJECTED
