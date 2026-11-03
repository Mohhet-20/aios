from release_platform.feature_flags.targeting_rules import deterministic_bucket, is_in_rollout


def test_deterministic_bucket_is_stable():
    b1 = deterministic_bucket("flag-a", "user-42")
    b2 = deterministic_bucket("flag-a", "user-42")
    assert b1 == b2
    assert 0.0 <= b1 < 100.0


def test_deterministic_bucket_varies_by_target():
    buckets = {deterministic_bucket("flag-a", f"user-{i}") for i in range(20)}
    assert len(buckets) > 1


def test_is_in_rollout_zero_pct_always_false():
    assert is_in_rollout("flag-a", "user-1", rollout_pct=0.0) is False


def test_is_in_rollout_full_pct_always_true():
    assert is_in_rollout("flag-a", "user-1", rollout_pct=100.0) is True


def test_is_in_rollout_matches_bucket_threshold():
    target = "user-99"
    bucket = deterministic_bucket("flag-a", target)
    assert is_in_rollout("flag-a", target, rollout_pct=bucket + 1) is True
    assert is_in_rollout("flag-a", target, rollout_pct=max(bucket - 1, 0)) is False
