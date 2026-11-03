"""Pure aggregation helpers over already-fetched analytics rows. No DB
or service imports, so these are trivially unit-testable in isolation
— the service layer is responsible for fetching rows and handing them
here, not for doing the counting/sorting itself."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone


def most_viewed(events: list, *, limit: int = 10) -> list[tuple[str, int]]:
    """events: objects with .event_type == 'page_view' and .subject_ref.
    Returns [(subject_ref, count), ...] sorted by count desc."""
    counts = Counter(e.subject_ref for e in events if e.event_type == "page_view" and e.subject_ref)
    return counts.most_common(limit)


def failed_search_rate(search_events: list) -> float:
    """search_events: objects with .event_metadata containing a
    'result_count' key. Returns the fraction with zero results."""
    if not search_events:
        return 0.0
    failed = sum(1 for e in search_events if e.event_metadata.get("result_count", 0) == 0)
    return failed / len(search_events)


def average_feedback_score(feedback_rows: list) -> float | None:
    if not feedback_rows:
        return None
    return sum(f.score for f in feedback_rows) / len(feedback_rows)


def tutorial_completion_rate(events: list) -> float:
    """events: objects with .event_type in {'tutorial_started', 'tutorial_completed'}."""
    started = sum(1 for e in events if e.event_type == "tutorial_started")
    completed = sum(1 for e in events if e.event_type == "tutorial_completed")
    if started == 0:
        return 0.0
    return min(completed / started, 1.0)


def content_freshness_score(last_reviewed_at: datetime | None, *, now: datetime, window_days: int) -> float:
    """1.0 = reviewed today, 0.0 = never reviewed or older than the window.
    Linear decay across the window."""
    if last_reviewed_at is None:
        return 0.0
    if last_reviewed_at.tzinfo is None:
        last_reviewed_at = last_reviewed_at.replace(tzinfo=timezone.utc)
    age_days = (now - last_reviewed_at).total_seconds() / 86400
    if age_days < 0:
        return 1.0
    if age_days >= window_days:
        return 0.0
    return 1.0 - (age_days / window_days)
