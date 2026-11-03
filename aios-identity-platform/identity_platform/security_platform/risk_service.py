"""RiskScoringService: a genuinely computed, deterministic risk score
for a login attempt — a weighted sum of concrete signals (new device,
new country, recent failed attempts, impossible-travel-style rapid
country change), not a fabricated ML prediction. Scores land in
[0, 1]; a score at or above `settings.risk_score_high_threshold`
produces a `SUSPICIOUS_LOGIN` security event so it shows up in the
audit trail even if the login itself is allowed to proceed."""
from __future__ import annotations

from dataclasses import dataclass, field

from identity_platform.config.settings import Settings, get_settings
from identity_platform.domain.enums import SecurityEventSeverity, SecurityEventType
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security_platform.security_event_service import SecurityEventService

_WEIGHT_NEW_DEVICE = 0.3
_WEIGHT_NEW_COUNTRY = 0.3
_WEIGHT_RECENT_FAILURES = 0.3
_WEIGHT_IMPOSSIBLE_TRAVEL = 0.4
_MAX_FAILURE_SIGNAL = 5


@dataclass
class RiskSignals:
    is_new_device: bool = False
    is_new_country: bool = False
    recent_failed_attempts: int = 0
    impossible_travel: bool = False
    raw: dict = field(default_factory=dict)


def compute_risk_score(signals: RiskSignals) -> float:
    score = 0.0
    if signals.is_new_device:
        score += _WEIGHT_NEW_DEVICE
    if signals.is_new_country:
        score += _WEIGHT_NEW_COUNTRY
    if signals.impossible_travel:
        score += _WEIGHT_IMPOSSIBLE_TRAVEL
    score += _WEIGHT_RECENT_FAILURES * min(signals.recent_failed_attempts, _MAX_FAILURE_SIGNAL) / _MAX_FAILURE_SIGNAL
    return round(min(score, 1.0), 4)


class RiskScoringService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.security_event_service = SecurityEventService(repos)

    async def score_and_record(
        self, *, user_id: str, organization_id: str | None, signals: RiskSignals,
    ) -> float:
        score = compute_risk_score(signals)
        if score >= self.settings.risk_score_high_threshold:
            severity = SecurityEventSeverity.CRITICAL if score >= 0.9 else SecurityEventSeverity.WARNING
            await self.security_event_service.record_event(
                event_type=SecurityEventType.SUSPICIOUS_LOGIN, severity=severity,
                organization_id=organization_id, user_id=user_id,
                details={"risk_score": score, **signals.raw},
            )
        return score
