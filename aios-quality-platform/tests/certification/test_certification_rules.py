from quality_platform.certification.certification_rules import compute_overall_score, decide_certification
from quality_platform.domain.enums import CertificationDecision

WEIGHTS = {"quality": 0.25, "reliability": 0.2, "security": 0.2, "performance": 0.2, "ai_quality": 0.15}


def test_compute_overall_score_all_categories():
    scores = {"quality": 90.0, "reliability": 90.0, "security": 90.0, "performance": 90.0, "ai_quality": 90.0}
    assert compute_overall_score(scores, WEIGHTS) == 90.0


def test_compute_overall_score_renormalizes_missing_categories():
    scores = {"quality": 100.0, "security": 60.0}
    # weights renormalized over just quality (0.25) and security (0.2)
    expected = (100.0 * 0.25 + 60.0 * 0.2) / (0.25 + 0.2)
    assert compute_overall_score(scores, WEIGHTS) == expected


def test_compute_overall_score_empty_scores_is_zero():
    assert compute_overall_score({}, WEIGHTS) == 0.0


def test_decide_certification_approved():
    assert decide_certification(85.0, min_score_for_approval=80.0) == CertificationDecision.APPROVED


def test_decide_certification_approved_with_conditions():
    assert decide_certification(75.0, min_score_for_approval=80.0) == CertificationDecision.APPROVED_WITH_CONDITIONS


def test_decide_certification_rejected():
    assert decide_certification(50.0, min_score_for_approval=80.0) == CertificationDecision.REJECTED
