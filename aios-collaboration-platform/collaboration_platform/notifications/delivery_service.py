"""NotificationDeliveryService: fans a notification out to every
channel the recipient's preferences enable and records one delivery
row per channel, then attempts delivery through a pluggable `Sender`
interface. In-app delivery is always immediate (a delivered in-app
notification just *is* the `NotificationModel` row existing — nothing
external to call). Email delivery goes through an injected sender;
the reference `NullEmailSender` shipped here logs the send and marks
it delivered rather than actually reaching an SMTP/provider API —
disclosed honestly (matching the Tool Platform's precedent for
categories it can't actually reach) rather than silently pretending
this platform has real outbound email. Swapping in a real
provider-backed sender (SES, SendGrid, etc.) behind the same `Sender`
protocol is a one-file change; nothing here has to change."""
from __future__ import annotations

from typing import Protocol

from collaboration_platform.database.base import utcnow
from collaboration_platform.domain.enums import DeliveryStatus, NotificationChannel
from collaboration_platform.models.notification import NotificationDeliveryModel, NotificationModel
from collaboration_platform.notifications.preference_service import NotificationPreferenceService
from collaboration_platform.repositories.registry import RepositoryRegistry


class Sender(Protocol):
    async def send(self, notification: NotificationModel) -> bool:
        """Returns True if delivery succeeded."""
        ...


class NullEmailSender:
    """Reference sender: does not contact any real email provider. It
    records what *would* have been sent and reports success, so the
    delivery pipeline is fully exercisable in tests/dev without a live
    SMTP dependency. `sent_log` is intentionally inspectable for tests."""

    def __init__(self) -> None:
        self.sent_log: list[str] = []

    async def send(self, notification: NotificationModel) -> bool:
        self.sent_log.append(f"[email stub] to={notification.recipient_id} title={notification.title!r}")
        return True


class NotificationDeliveryService:
    def __init__(self, repos: RepositoryRegistry, *, email_sender: Sender | None = None):
        self.repos = repos
        self.email_sender = email_sender or NullEmailSender()
        self.preferences = NotificationPreferenceService(repos)

    async def fan_out(self, notification: NotificationModel) -> list[NotificationDeliveryModel]:
        effective = await self.preferences.get_effective(notification.recipient_id, notification.notification_type)
        deliveries: list[NotificationDeliveryModel] = []

        if effective["in_app_enabled"]:
            deliveries.append(await self.repos.notification_deliveries.add(NotificationDeliveryModel(
                notification_id=notification.id, channel=NotificationChannel.IN_APP.value,
                status=DeliveryStatus.SENT.value, delivered_at=utcnow(),
            )))

        if effective["email_enabled"]:
            delivery = await self.repos.notification_deliveries.add(NotificationDeliveryModel(
                notification_id=notification.id, channel=NotificationChannel.EMAIL.value,
            ))
            deliveries.append(await self._attempt_delivery(delivery, notification))

        if effective["digest_enabled"]:
            deliveries.append(await self.repos.notification_deliveries.add(NotificationDeliveryModel(
                notification_id=notification.id, channel=NotificationChannel.DIGEST.value,
                status=DeliveryStatus.PENDING.value,  # collected later by DigestService, not sent per-event
            )))

        return deliveries

    async def _attempt_delivery(self, delivery: NotificationDeliveryModel, notification: NotificationModel) -> NotificationDeliveryModel:
        try:
            succeeded = await self.email_sender.send(notification)
        except Exception as exc:  # noqa: BLE001 — a sender failure must not raise into the caller's write path
            delivery.status = DeliveryStatus.FAILED.value
            delivery.error = str(exc)
            return await self.repos.notification_deliveries.update(delivery)
        if succeeded:
            delivery.status = DeliveryStatus.SENT.value
            delivery.delivered_at = utcnow()
        else:
            delivery.status = DeliveryStatus.FAILED.value
            delivery.error = "sender reported failure"
        return await self.repos.notification_deliveries.update(delivery)
