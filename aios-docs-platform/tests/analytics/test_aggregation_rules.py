from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from docs_platform.analytics.aggregation_rules import (
    average_feedback_score,
    content_freshness_score,
    failed_search_rate,
    most_viewed,
    tutorial_completion_rate,
)


def test_most_viewed_counts_page_views_only():
    events = [
        SimpleNamespace(event_type="page_view", subject_ref="page:1"),
        SimpleNamespace(event_type="page_view", subject_ref="page:1"),
        SimpleNamespace(event_type="page_view", subject_ref="page:2"),
        SimpleNamespace(event_type="search_query", subject_ref="page:1"),
    ]
    result = most_viewed(events)
    assert result[0] == ("page:1", 2)
    assert ("page:2", 1) in result


def test_failed_search_rate_empty_is_zero():
    assert failed_search_rate([]) == 0.0


def test_failed_search_rate_computes_fraction():
    events = [
        SimpleNamespace(event_metadata={"result_count": 0}),
        SimpleNamespace(event_metadata={"result_count": 3}),
        SimpleNamespace(event_metadata={"result_count": 0}),
        SimpleNamespace(event_metadata={"result_count": 5}),
    ]
    assert failed_search_rate(events) == 0.5


def test_average_feedback_score_none_when_empty():
    assert average_feedback_score([]) is None


def test_average_feedback_score_computes_mean():
    rows = [SimpleNamespace(score=4), SimpleNamespace(score=2)]
    assert average_feedback_score(rows) == 3.0


def test_tutorial_completion_rate_no_starts_is_zero():
    assert tutorial_completion_rate([]) == 0.0


def test_tutorial_completion_rate_computes_ratio():
    events = (
        [SimpleNamespace(event_type="tutorial_started")] * 4
        + [SimpleNamespace(event_type="tutorial_completed")] * 3
    )
    assert tutorial_completion_rate(events) == 0.75


def test_content_freshness_score_never_reviewed_is_zero():
    now = datetime.now(timezone.utc)
    assert content_freshness_score(None, now=now, window_days=90) == 0.0


def test_content_freshness_score_reviewed_today_is_one():
    now = datetime.now(timezone.utc)
    assert content_freshness_score(now, now=now, window_days=90) == 1.0


def test_content_freshness_score_decays_linearly():
    now = datetime.now(timezone.utc)
    reviewed = now - timedelta(days=45)
    score = content_freshness_score(reviewed, now=now, window_days=90)
    assert abs(score - 0.5) < 0.01


def test_content_freshness_score_beyond_window_is_zero():
    now = datetime.now(timezone.utc)
    reviewed = now - timedelta(days=200)
    assert content_freshness_score(reviewed, now=now, window_days=90) == 0.0


def test_content_freshness_score_handles_naive_datetime():
    now = datetime.now(timezone.utc)
    reviewed_naive = (now - timedelta(days=10)).replace(tzinfo=None)
    score = content_freshness_score(reviewed_naive, now=now, window_days=90)
    assert 0.0 < score < 1.0
