from docs_platform.versioning.diff_rules import compute_diff


def test_compute_diff_shows_changed_lines():
    old = "line one\nline two\n"
    new = "line one\nline TWO\n"
    diff = compute_diff(old, new)
    assert any("line two" in line for line in diff)
    assert any("line TWO" in line for line in diff)


def test_compute_diff_identical_text_is_empty():
    assert compute_diff("same", "same") == []
