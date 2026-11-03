"""Escalation policies + delivery. An `EscalationPolicyModel.levels`
list looks like `[{"level": 1, "delay_minutes": 0, "targets": ["<channel_id>", ...]}, ...]`.
`escalate` advances a firing alert to its next configured level and
records + "sends" a notification per target channel.

`NullNotificationSender` is the same honestly-disclosed-gap pattern as
`NullEmailSender` in the Collaboration Platform: it logs what it would
have sent through Slack/PagerDuty/SMS/webhook/email and reports success
without a live integration, because this build doesn't have credentials
to any of those providers. Swapping in a real sender is a one-class
change behind the `Sender` protocol every call site already uses."""
from __future__ import annotations

from typing import Protocol

import structlog

from observability_platform.config.settings import Settings, get_settings
from observability_platform.core.exceptions import EscalationPolicyError
from observability_platform.database.base import utcnow
from observability_platform.models.alerts import AlertEscalationModel, AlertNotificationModel
from observability_platform.repositories.registry import RepositoryRegistry

logger = structlog.get_logger(__name__)


class Sender(Protocol):
    async def send(self, channel_type: str, target: str, message: str) -> bool: ...


class NullNotificationSender:
    """Reference implementation with no live integration — logs the
    would-be delivery and reports success."""

    async def send(self, channel_type: str, target: str, message: str) -> bool:
        logger.info("notification.would_send", channel_type=channel_type, target=target, message=message)
        return True


class AlertEscalationService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None, sender: Sender | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.sender = sender or NullNotificationSender()

    async def escalate(self, tenant_id: str, alert_id: str) -> list[AlertEscalationModel]:
        alert = await self.repos.alerts.get_or_404(alert_id)
        if alert.status != "firing":
            return []  # only actively-firing alerts escalate
        if not alert.rule_id:
            return []
        rule = await self.repos.alert_rules.get(alert.rule_id)
        if rule is None or not rule.escalation_policy_id:
            return []
        policy = await self.repos.escalation_policies.get_or_404(rule.escalation_policy_id)

        current_level = await self.repos.alert_escalations.highest_level_for_alert(tenant_id, alert_id)
        next_level = current_level + 1
        if next_level > len(policy.levels):
            return []  # already at the top of the policy — nothing further to escalate to
        if next_level > self.settings.max_escalation_levels:
            raise EscalationPolicyError(
                f"Escalation would exceed the platform maximum of {self.settings.max_escalation_levels} levels"
            )

        level_def = policy.levels[next_level - 1]
        records = []
        for target in level_def.get("targets", []):
            record = await self.repos.alert_escalations.add(
                AlertEscalationModel(tenant_id=tenant_id, alert_id=alert_id, policy_id=policy.id, level=next_level, target=target)
            )
            records.append(record)
            await self._notify(tenant_id, alert, channel_id=target)
        return records

    async def _notify(self, tenant_id: str, alert, *, channel_id: str) -> AlertNotificationModel:
        channel = await self.repos.notification_channels.get(channel_id)
        channel_type = channel.channel_type if channel else "webhook"
        notification = AlertNotificationModel(tenant_id=tenant_id, alert_id=alert.id, channel_id=channel_id, status="pending")
        notification = await self.repos.alert_notifications.add(notification)
        try:
            ok = await self.sender.send(channel_type, channel_id, f"Alert: {alert.title}")
            notification.status = "sent" if ok else "failed"
            notification.sent_at = utcnow() if ok else None
        except Exception as exc:  # pragma: no cover - defensive
            notification.status = "failed"
            notification.error_message = str(exc)
        return await self.repos.alert_notifications.update(notification)
