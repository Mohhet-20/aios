"""Statistical primitives for experiment analysis: Welch's t-test (unequal
variance, unequal sample size), confidence intervals, effect size, and
winner selection. No numpy/scipy dependency — the regularized incomplete
beta function (the one genuinely nontrivial piece of a real t-test) is
implemented directly on top of `math.lgamma`, which is exact log-gamma
from the stdlib, so the resulting p-values are not a normal-distribution
approximation but the real Student-t CDF.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field

_MAX_ITER = 200
_EPS = 1e-10
_FPMIN = 1e-300


def _betacf(a: float, b: float, x: float) -> float:
    """Continued-fraction evaluation used by the regularized incomplete
    beta function (standard Numerical-Recipes-style algorithm)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, _MAX_ITER + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return h


def _betainc(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    bt = math.exp(log_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def two_tailed_p_from_t(t: float, df: float) -> float:
    """Exact two-tailed p-value for a Student-t statistic with `df`
    degrees of freedom, via I_{df/(df+t^2)}(df/2, 1/2)."""
    if df <= 0:
        return 1.0
    t = abs(t)
    x = df / (df + t * t)
    return _betainc(x, df / 2.0, 0.5)


def t_critical(df: float, *, confidence: float = 0.95) -> float:
    """Two-tailed critical t-value for the given confidence level, found
    by bisection against `two_tailed_p_from_t` (monotonically decreasing
    in t), so it stays consistent with the same exact CDF used above."""
    target = 1 - confidence
    lo, hi = 0.0, 1000.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if two_tailed_p_from_t(mid, df) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@dataclass
class SampleSummary:
    n: int
    mean: float
    stddev: float
    minimum: float
    maximum: float


def summarize(sample: list[float]) -> SampleSummary:
    if not sample:
        return SampleSummary(n=0, mean=0.0, stddev=0.0, minimum=0.0, maximum=0.0)
    return SampleSummary(
        n=len(sample), mean=statistics.mean(sample),
        stddev=statistics.stdev(sample) if len(sample) > 1 else 0.0,
        minimum=min(sample), maximum=max(sample),
    )


@dataclass
class WelchTTestResult:
    t_stat: float
    df: float
    p_value: float
    mean_diff: float
    ci_low: float
    ci_high: float
    cohens_d: float
    significant: bool


def welch_t_test(sample_a: list[float], sample_b: list[float], *, alpha: float = 0.05, confidence: float = 0.95) -> WelchTTestResult:
    n1, n2 = len(sample_a), len(sample_b)
    if n1 < 2 or n2 < 2:
        # Not enough data for a variance estimate — report the raw mean
        # difference with no statistical claim attached.
        diff = (statistics.mean(sample_a) if sample_a else 0.0) - (statistics.mean(sample_b) if sample_b else 0.0)
        return WelchTTestResult(t_stat=0.0, df=0.0, p_value=1.0, mean_diff=diff, ci_low=diff, ci_high=diff, cohens_d=0.0, significant=False)

    m1, m2 = statistics.mean(sample_a), statistics.mean(sample_b)
    v1, v2 = statistics.variance(sample_a), statistics.variance(sample_b)
    se_sq = v1 / n1 + v2 / n2
    se = math.sqrt(se_sq) if se_sq > 0 else 0.0
    diff = m1 - m2

    if se == 0:
        return WelchTTestResult(t_stat=0.0, df=float(n1 + n2 - 2), p_value=1.0, mean_diff=diff, ci_low=diff, ci_high=diff, cohens_d=0.0, significant=False)

    t_stat = diff / se
    df_numerator = se_sq ** 2
    df_denominator = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    df = df_numerator / df_denominator if df_denominator > 0 else float(n1 + n2 - 2)
    p_value = two_tailed_p_from_t(t_stat, df)

    tcrit = t_critical(df, confidence=confidence)
    margin = tcrit * se

    pooled_sd = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)) if (n1 + n2 - 2) > 0 else 0.0
    cohens_d = diff / pooled_sd if pooled_sd > 0 else 0.0

    return WelchTTestResult(
        t_stat=t_stat, df=df, p_value=p_value, mean_diff=diff,
        ci_low=diff - margin, ci_high=diff + margin, cohens_d=cohens_d, significant=p_value < alpha,
    )


@dataclass
class WinnerSelection:
    leader_variant_id: str | None
    means: dict[str, float] = field(default_factory=dict)
    comparisons: dict[str, dict] = field(default_factory=dict)
    significant_winner: bool = False


def select_winner(variant_scores: dict[str, list[float]], *, higher_is_better: bool = True, alpha: float = 0.05) -> WinnerSelection:
    """Picks the variant with the best mean score, then runs a pairwise
    Welch's t-test against every other variant. `significant_winner` is
    True only if the leader beats *every* other variant at the given
    alpha — a leader that merely has the best mean without statistical
    separation is still reported (as `leader_variant_id`), just flagged
    as not yet a confirmed winner."""
    means = {vid: (statistics.mean(scores) if scores else float("-inf") if higher_is_better else float("inf")) for vid, scores in variant_scores.items()}
    if not means:
        return WinnerSelection(leader_variant_id=None)

    leader_id = max(means, key=lambda vid: means[vid]) if higher_is_better else min(means, key=lambda vid: means[vid])
    comparisons: dict[str, dict] = {}
    all_significant = True
    for vid, scores in variant_scores.items():
        if vid == leader_id:
            continue
        result = welch_t_test(variant_scores[leader_id], scores, alpha=alpha)
        favors_leader = (result.mean_diff > 0) if higher_is_better else (result.mean_diff < 0)
        is_significant = result.significant and favors_leader
        comparisons[vid] = {
            "p_value": result.p_value, "t_stat": result.t_stat, "cohens_d": result.cohens_d,
            "mean_diff": result.mean_diff, "ci_low": result.ci_low, "ci_high": result.ci_high,
            "significant": is_significant,
        }
        if not is_significant:
            all_significant = False

    return WinnerSelection(
        leader_variant_id=leader_id, means=means, comparisons=comparisons,
        significant_winner=all_significant and len(variant_scores) > 1,
    )
