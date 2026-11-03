"""Alert rule evaluation and firing.

Condition evaluation is intentionally simple and honestly scoped:
threshold rules compare the latest metric value against a fixed
operator/value pair; anomaly rules compute the mean and population
standard deviation of the preceding `baseline_window_points` samples
and flag a breach when the newest value is more than
`deviation_multiplier` standard deviations from that mean. This is a
real, working anomaly check — but it is a classic statistical
z-score test, not a trained ML model, and callers with genuinely
seasonal or multimodal metrics should not expect it to out-perform a
real anomaly-detection service. That's a disclosed scope boundary, the
same posture as the Collaboration Platform's semantic-search gap.

Firing is deduplicated per `(rule_id, component_id)` via `dedup_key`:
re-evaluating a still-breaching rule updates the existing open alert's
`context`/`fired_at`-adjacent fields in place rather than creating a
duplicate. Because "does an active alert for this dedup_key already
exist, then create-or-update" is a check-then-act sequence spanning
multiple statements, it's serialized per dedup_key with an in-process
`asyncio.Lock` held across the read, the write, AND the commit — the
same commit-spanning-lock pattern established for
`EditSessionService.start_session` (Collaboration Platform) and
`SessionService.create_session` (Identity Platform), for the identical
reason: separate callers own separate DB connections, and SQLite only
makes one connection's write visible to another once it commits."""
from __future__ import annotations

import asyncio
import statistics
from collections import defaultdict

from observability_platform.alerts.maintenance_window_service import MaintenanceWindowService
from observability_platform.config.settings import Settings, get_settings
from observability_platform.core.exceptions import ValidationError
from observability_platform.database.base import utcnow
from observability_platform.domain.entities import Alert as AlertEntity
from observability_platform.domain.enums import AlertStatus
from observability_platform.models.alerts import AlertModel, AlertRuleModel
from observability_platform.repositories.registry import RepositoryRegistry


def _to_entity(model: AlertModel) -> AlertEntity:
    return AlertEntity(id=model.id, status=AlertStatus(model.status))


def evaluate_threshold(value: float, condition: dict) -> bool:
    operator = condition.get("operator", "gt")
    threshold = condition["value"]
    ops = {
        "gt": lambda v, t: v > t,
        "gte": lambda v, t: v >= t,
        "lt": lambda v, t: v < t,
        "lte": lambda v, t: v <= t,
        "eq": lambda v, t: v == t,
    }
    if operator not in ops:
        raise ValidationError(f"Unknown threshold operator '{operator}'")
    return ops[operator](value, threshold)


def evaluate_anomaly(value: float, baseline: list[float], condition: dict) -> bool:
    if len(baseline) < 2:
        return False  # not enough history to establish a baseline
    mean = statistics.mean(baseline)
    stdev = statistics.pstdev(baseline)
    if stdev == 0:
        return value != mean
    multiplier = condition.get("deviation_multiplier", 3.0)
    return abs(value - mean) > multiplier * stdev


class AlertEvaluationService:
    _dedup_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.maintenance = MaintenanceWindowService(repos)

    def _dedup_key(self, rule_id: str, component_id: str | None) -> str:
        return f"{rule_id}:{component_id or 'global'}"

    async def fire_or_update(
        self, tenant_id: str, rule: AlertRuleModel, *, component_id: str | None, context: dict
    ) -> AlertModel | None:
        if component_id and await self.maintenance.is_alert_suppressed(tenant_id, component_id):
            return None

        dedup_key = self._dedup_key(rule.id, component_id)
        async with self._dedup_locks[dedup_key]:
            existing = await self.repos.alerts.find_active_by_dedup_key(tenant_id, dedup_key)
            if existing is not None:
                existing.context = {**existing.context, **context}
                updated = await self.repos.alerts.update(existing)
                await self.repos.session.commit()
                return updated

            alert = AlertModel(
                tenant_id=tenant_id, rule_id=rule.id, alert_type=rule.alert_type, severity=rule.severity,
                status=AlertStatus.FIRING.value, title=f"{rule.name} breached", component_id=component_id,
                dedup_key=dedup_key, context=context,
            )
            created = await self.repos.alerts.add(alert)
            await self.repos.session.commit()
            return created

    async def auto_resolve_if_healed(self, tenant_id: str, rule: AlertRuleModel, *, component_id: str | None) -> AlertModel | None:
        dedup_key = self._dedup_key(rule.id, component_id)
        async with self._dedup_locks[dedup_key]:
            existing = await self.repos.alerts.find_active_by_dedup_key(tenant_id, dedup_key)
            if existing is None:
                return None
            entity = _to_entity(existing)
            entity.resolve()
            existing.status = entity.status.value
            existing.resolved_at = entity.resolved_at
            resolved = await self.repos.alerts.update(existing)
            await self.repos.session.commit()
            return resolved

    async def evaluate_rule(self, tenant_id: str, rule: AlertRuleModel, *, component_id: str | None = None) -> AlertModel | None:
        if not rule.metric_name:
            return None
        latest = await self.repos.metric_points.latest(tenant_id, rule.metric_name, component_id=component_id)
        if latest is None:
            return None

        breached: bool
        if rule.condition.get("baseline_window_points") is not None:
            history = await self.repos.metric_points.query_range(
                tenant_id, rule.metric_name, component_id=component_id,
                limit=rule.condition["baseline_window_points"] + 1,
            )
            baseline = [p.value for p in history[:-1]] if len(history) > 1 else []
            breached = evaluate_anomaly(latest.value, baseline, rule.condition)
        else:
            breached = evaluate_threshold(latest.value, rule.condition)

        if breached:
            return await self.fire_or_update(
                tenant_id, rule, component_id=component_id, context={"value": latest.value, "evaluated_at": utcnow().isoformat()}
            )
        return await self.auto_resolve_if_healed(tenant_id, rule, component_id=component_id)
