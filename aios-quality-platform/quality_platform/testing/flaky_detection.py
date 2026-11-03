"""Pure functions for flaky-test detection — no DB/service imports, so
they're trivially unit-testable and reusable from both the service
layer and any future batch job. A test case is "flaky" not because it
fails, but because it *disagrees with its own recent history*: it
passes sometimes and fails other times on what should be a
deterministic check. We measure that as the number of pass<->fail
transitions within the most recent `history_window` results, ordered
newest-first (the shape `TestCaseResultRepository.list_for_case`
already returns)."""
from __future__ import annotations

_FLAKY_RELEVANT = {"passed", "failed"}


def count_transitions(results_newest_first: list[str]) -> int:
    """Counts adjacent pass<->fail flips in the given order. Results
    that aren't "passed" or "failed" (skipped, error) are dropped
    first since they don't represent a determinism disagreement."""
    relevant = [r for r in results_newest_first if r in _FLAKY_RELEVANT]
    transitions = 0
    for prev, cur in zip(relevant, relevant[1:]):
        if prev != cur:
            transitions += 1
    return transitions


def is_flaky(results_newest_first: list[str], *, threshold: int) -> bool:
    return count_transitions(results_newest_first) >= threshold
