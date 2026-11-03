"""Pure trend-direction analysis over an ascending-order value series
— no DB/service imports. Splits the series into an older and newer
half and compares their averages rather than just comparing first vs.
last point, so a single noisy reading at either end doesn't flip the
verdict."""
from __future__ import annotations

DEFAULT_STABLE_BAND_PCT = 2.0


def compute_trend_direction(values_ascending: list[float], *, stable_band_pct: float = DEFAULT_STABLE_BAND_PCT) -> str:
    """Returns "improving", "declining", or "stable". Needs at least
    two points to say anything; fewer than that is "stable" by
    definition (nothing to compare)."""
    if len(values_ascending) < 2:
        return "stable"

    midpoint = len(values_ascending) // 2
    older_half = values_ascending[:midpoint] or values_ascending[:1]
    newer_half = values_ascending[midpoint:]
    older_avg = sum(older_half) / len(older_half)
    newer_avg = sum(newer_half) / len(newer_half)

    if older_avg == 0:
        return "stable" if newer_avg == 0 else ("improving" if newer_avg > 0 else "declining")

    change_pct = (newer_avg - older_avg) / abs(older_avg) * 100.0
    if abs(change_pct) < stable_band_pct:
        return "stable"
    return "improving" if change_pct > 0 else "declining"
