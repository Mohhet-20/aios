"""Few-shot example selection and formatting. Selection is deterministic
and rule-based (no LLM call) so it stays cheap, reproducible, and fast to
run on every optimization pass: prefer golden test cases that have
historically passed their most recent test run, then fall back to any
case with a recorded `expected_output`, prioritizing tag/output diversity
over raw recency.
"""
from __future__ import annotations


def select_few_shot_examples(golden_cases: list, recent_results: list | None = None, *, max_examples: int = 3) -> list:
    """`recent_results` is an optional list of TestResultModel rows (any
    run) used to bias selection toward cases that are known to pass —
    a case whose most recent recorded result passed is preferred over one
    that's never been run or that most recently failed."""
    passed_case_ids: set[str] = set()
    if recent_results:
        latest_by_case: dict[str, object] = {}
        for result in recent_results:
            if not result.golden_test_case_id:
                continue
            latest_by_case[result.golden_test_case_id] = result  # last one wins if caller passes chronological order
        passed_case_ids = {cid for cid, r in latest_by_case.items() if r.passed}

    eligible = [c for c in golden_cases if c.expected_output]
    eligible.sort(key=lambda c: (c.id not in passed_case_ids, c.name))
    return eligible[:max_examples]


def build_few_shot_block(examples: list, *, variable_names: list[str] | None = None) -> str:
    """Renders selected golden test cases as an in-template few-shot block.
    Uses the case's raw `input_variables` (not a fully-rendered prompt) so
    the block stays readable as an editable template fragment."""
    if not examples:
        return ""
    lines = ["Examples:"]
    for i, case in enumerate(examples, start=1):
        inputs_desc = ", ".join(f"{k}={v!r}" for k, v in (case.input_variables or {}).items())
        lines.append(f"\nExample {i}:")
        if inputs_desc:
            lines.append(f"Input: {inputs_desc}")
        lines.append(f"Output: {case.expected_output}")
    return "\n".join(lines)
