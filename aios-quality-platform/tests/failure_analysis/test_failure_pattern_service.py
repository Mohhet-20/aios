import pytest

from quality_platform.failure_analysis.failure_pattern_service import FailurePatternService

pytestmark = pytest.mark.asyncio


async def test_record_occurrence_creates_new_pattern(repos):
    svc = FailurePatternService(repos)
    pattern = await svc.record_occurrence("t1", pattern_type="flaky_test", subject_ref="test:probe-1")
    assert pattern.occurrences == 1
    assert svc.is_recurring(pattern) is False


async def test_record_occurrence_increments_existing_pattern(repos):
    svc = FailurePatternService(repos)
    first = await svc.record_occurrence("t1", pattern_type="memory_leak", subject_ref="svc:probe-2")
    second = await svc.record_occurrence("t1", pattern_type="memory_leak", subject_ref="svc:probe-2")
    third = await svc.record_occurrence("t1", pattern_type="memory_leak", subject_ref="svc:probe-2")
    assert first.id == second.id == third.id
    assert third.occurrences == 3
    assert svc.is_recurring(third) is True  # default threshold is 3


async def test_record_occurrence_merges_details(repos):
    svc = FailurePatternService(repos)
    await svc.record_occurrence("t1", pattern_type="concurrency_issue", subject_ref="svc:probe-3", details={"a": 1})
    updated = await svc.record_occurrence("t1", pattern_type="concurrency_issue", subject_ref="svc:probe-3", details={"b": 2})
    assert updated.details == {"a": 1, "b": 2}


async def test_list_patterns_filters_by_min_occurrences(repos):
    svc = FailurePatternService(repos)
    await svc.record_occurrence("t1", pattern_type="root_cause", subject_ref="svc:probe-4")
    await svc.record_occurrence("t1", pattern_type="root_cause", subject_ref="svc:probe-5")
    await svc.record_occurrence("t1", pattern_type="root_cause", subject_ref="svc:probe-5")

    recurring = await svc.list_patterns("t1", pattern_type="root_cause", min_occurrences=2)
    assert len(recurring) == 1
    assert recurring[0].subject_ref == "svc:probe-5"
