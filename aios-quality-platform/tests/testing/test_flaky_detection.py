from quality_platform.testing.flaky_detection import count_transitions, is_flaky


def test_count_transitions_stable_pass():
    assert count_transitions(["passed", "passed", "passed"]) == 0


def test_count_transitions_alternating():
    assert count_transitions(["passed", "failed", "passed", "failed"]) == 3


def test_count_transitions_ignores_skipped_and_error():
    assert count_transitions(["passed", "skipped", "failed", "error", "passed"]) == 2


def test_is_flaky_threshold():
    assert is_flaky(["passed", "failed", "passed"], threshold=2) is True
    assert is_flaky(["passed", "failed", "passed"], threshold=3) is False
