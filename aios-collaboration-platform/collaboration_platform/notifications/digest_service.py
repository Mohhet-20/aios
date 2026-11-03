"""DigestService: batches a user's digest-channel notifications into
one rolled-up digest notification, capped at
`notification_digest_batch_size` per digest so a very active workspace
can't produce an unreadable wall of a single digest — remaining items
carry over to the next digest run rather than being dropped."""
from __future__ import annotations

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.database.base import utcnow
from collaboration_platform.domain.enums import DeliveryStatus, NotificationChannel, NotificationType
from collaboration_platform.models.notification import NotificationModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class DigestService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def build_digest(self, user_id: str) -> NotificationModel | None:
        pending_deliveries = await self.repos.notification_deliveries.list_by_status(
            DeliveryStatus.PENDING.value, limit=self.settings.notification_digest_batch_size,
        )
        # only this user's digest-channel deliveries
        own_pending = []
        for delivery in pending_deliveries:
            if delivery.channel != NotificationChannel.DIGEST.value:
                continue
            source = await self.repos.notifications.get(delivery.notification_id)
            if source is not None and source.recipient_id == user_id:
                own_pending.append((delivery, source))

        if not own_pending:
            return None

        lines = [f"- {source.title}" for _, source in own_pending]
        digest = await self.repos.notifications.add(NotificationModel(
            recipient_id=user_id, notification_type=NotificationType.DIGEST.value,
            title=f"Digest: {len(own_pending)} update(s)", body="\n".join(lines),
        ))
        for delivery, _ in own_pending:
            delivery.status = DeliveryStatus.SENT.value
            delivery.delivered_at = utcnow()
            await self.repos.notification_deliveries.update(delivery)
        return digest
