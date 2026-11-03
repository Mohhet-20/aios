"""Pure SLO status classification and error-budget arithmetic — no
DB/service imports."""
from __future__ import annotations

from quality_platform.domain.enums import SloStatus

DEFAULT_AT_RISK_MARGIN_PCT = 0.5


def classify_slo_status(current_pct: float, target_pct: float, *, at_risk_margin_pct: float = DEFAULT_AT_RISK_MARGIN_PCT) -> SloStatus:
    """Breached once the current value drops below target; at_risk
    while it's above target but within `at_risk_margin_pct` of it
    (comfortably meeting the SLO today, but one bad day from
    breaching); meeting otherwise."""
    if current_pct < target_pct:
        return SloStatus.BREACHED
    if current_pct < target_pct + at_risk_margin_pct:
        return SloStatus.AT_RISK
    return SloStatus.MEETING


def compute_error_budget_remaining_pct(current_pct: float, target_pct: float) -> float:
    """What fraction of the allowed error budget (100 - target) is
    still unspent, as a percentage. 100% = no errors consumed yet;
    0% = exactly at budget; negative = over budget (breached). A
    target of 100% has no error budget to spend at all -- treated as
    fully consumed (0%) the instant current drops below it, and fully
    remaining (100%) otherwise, since there's no meaningful ratio to
    compute against a zero-width budget."""
    budget_pct = 100.0 - target_pct
    if budget_pct <= 0:
        return 100.0 if current_pct >= target_pct else 0.0
    consumed_pct = target_pct - current_pct
    return (1 - consumed_pct / budget_pct) * 100.0
