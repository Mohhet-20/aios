"""Pure targeting helpers — no DB or service imports. Percentage
rollouts and A/B/experiment bucketing need a stable, deterministic
mapping from (flag, target) to a 0-100 "bucket" so the same target
always lands in the same bucket across repeated evaluations (otherwise
a user could flicker in and out of a rollout on every request). MD5
is used here purely as a fast, well-distributed non-cryptographic
hash — never for anything security-sensitive."""
from __future__ import annotations

import hashlib


def deterministic_bucket(flag_key: str, target_ref: str) -> float:
    """Returns a stable value in [0.0, 100.0) for (flag_key, target_ref)."""
    digest = hashlib.md5(f"{flag_key}:{target_ref}".encode("utf-8")).hexdigest()
    bucket_int = int(digest[:8], 16)
    return (bucket_int % 10_000) / 100.0


def is_in_rollout(flag_key: str, target_ref: str, *, rollout_pct: float) -> bool:
    if rollout_pct >= 100.0:
        return True
    if rollout_pct <= 0.0:
        return False
    return deterministic_bucket(flag_key, target_ref) < rollout_pct
