import pytest

from quality_platform.core.exceptions import ValidationError
from quality_platform.failure_analysis.risk_assessment_service import RiskAssessmentService

pytestmark = pytest.mark.asyncio


async def test_assess_requires_at_least_one_factor(repos):
    svc = RiskAssessmentService(repos)
    with pytest.raises(ValidationError):
        await svc.assess("t1", "rel:1", factors={})


async def test_assess_computes_mean_and_classifies(repos):
    svc = RiskAssessmentService(repos)
    assessment = await svc.assess("t1", "rel:2", factors={"regression_severity": 90.0, "open_findings": 90.0})
    assert assessment.risk_score == 90.0
    assert assessment.risk_level == "critical"


async def test_latest_returns_most_recent(repos):
    svc = RiskAssessmentService(repos)
    await svc.assess("t1", "rel:3", factors={"a": 10.0})
    second = await svc.assess("t1", "rel:3", factors={"a": 80.0})
    latest = await svc.latest("t1", "rel:3")
    assert latest.id == second.id


async def test_list_history_returns_all(repos):
    svc = RiskAssessmentService(repos)
    await svc.assess("t1", "rel:4", factors={"a": 10.0})
    await svc.assess("t1", "rel:4", factors={"a": 20.0})
    history = await svc.list_history("t1", "rel:4")
    assert len(history) == 2
