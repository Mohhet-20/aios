"""Threat-signal detectors. Rate/window-based detectors (brute force,
API abuse, tool abuse) and the privilege-escalation/credential-abuse
checks are deterministic threshold heuristics on caller-supplied
event data — this module does not itself track event history; the
caller (an auth flow, the API gateway, a workflow runner) is
responsible for supplying the relevant recent timestamps or counts,
the same "caller owns collection, detector owns judgment" split used
by the guardrail detectors. Anomaly detection is a real, working
z-score check against a caller-supplied numeric baseline — not a
trained model, the same disclosed-gap posture as everywhere else in
this platform that does heuristic detection rather than ML inference."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _count_in_window(timestamps: list[datetime], window_seconds: int) -> int:
    if not timestamps:
        return 0
    aware_ts = sorted(_aware(t) for t in timestamps)
    latest = aware_ts[-1]
    cutoff = latest.timestamp() - window_seconds
    return sum(1 for t in aware_ts if t.timestamp() >= cutoff)


def detect_brute_force(attempt_timestamps: list[datetime], *, threshold: int, window_seconds: int) -> bool:
    return _count_in_window(attempt_timestamps, window_seconds) >= threshold


def detect_api_abuse(request_timestamps: list[datetime], *, threshold: int, window_seconds: int) -> bool:
    return _count_in_window(request_timestamps, window_seconds) >= threshold


def detect_tool_abuse(call_timestamps: list[datetime], *, threshold: int, window_seconds: int) -> bool:
    return _count_in_window(call_timestamps, window_seconds) >= threshold


def detect_privilege_escalation(previous_role_rank: int, new_role_rank: int, *, approved: bool) -> bool:
    """Flags an unapproved jump to a higher-privilege role. A rank
    increase that went through a proper approval workflow is not a
    threat signal — this only fires for privilege gained *without*
    approval."""
    return new_role_rank > previous_role_rank and not approved


def detect_credential_abuse(distinct_source_count: int, *, threshold: int = 3) -> bool:
    """Same credential used from more than `threshold` distinct
    sources (IPs/devices) within a short window — a proxy for
    credential sharing or theft, since the caller is responsible for
    bucketing "recent" appropriately before counting distinct sources."""
    return distinct_source_count >= threshold


def detect_suspicious_workflow(step_count: int, external_call_count: int, *, max_steps: int = 50, max_external_calls: int = 20) -> bool:
    """Unusually large workflows (excessive step count or external
    calls) are a reasonable first-line proxy for a workflow being
    abused as an exfiltration or resource-exhaustion vector."""
    return step_count > max_steps or external_call_count > max_external_calls


@dataclass
class AnomalyResult:
    is_anomaly: bool
    z_score: float


def detect_anomaly(value: float, baseline: list[float], *, z_threshold: float = 3.0) -> AnomalyResult:
    """Standard z-score anomaly check: how many standard deviations is
    `value` from the mean of `baseline`. Needs at least 2 baseline
    points to compute a standard deviation; fewer than that, nothing
    can be judged anomalous yet."""
    if len(baseline) < 2:
        return AnomalyResult(is_anomaly=False, z_score=0.0)
    mean = statistics.mean(baseline)
    stdev = statistics.pstdev(baseline)
    if stdev == 0:
        return AnomalyResult(is_anomaly=value != mean, z_score=0.0 if value == mean else float("inf"))
    z = (value - mean) / stdev
    return AnomalyResult(is_anomaly=abs(z) >= z_threshold, z_score=z)


@dataclass
class BehaviorResult:
    is_deviant: bool
    novel_actions: list[str] = field(default_factory=list)


def detect_behavior_deviation(recent_actions: list[str], typical_actions: set[str], *, min_sample: int = 3) -> BehaviorResult:
    """Novelty-based behavior check: actions performed that never
    appear in the entity's established baseline. Needs a minimum
    sample of recent actions before judging deviation, to avoid
    flagging on a single early observation."""
    if len(recent_actions) < min_sample:
        return BehaviorResult(is_deviant=False)
    novel = sorted({a for a in recent_actions if a not in typical_actions})
    return BehaviorResult(is_deviant=bool(novel), novel_actions=novel)
