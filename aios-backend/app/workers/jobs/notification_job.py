"""Fan-out delivery of a notification to external channels (email, Slack,
webhook) once those integrations exist. Today, notifications are created
directly in the database by services/event handlers and read via the
Notification API; this job is the seam for asynchronous external delivery."""

from app.logging.setup import get_logger

logger = get_logger(__name__)


async def deliver_notification(notification_id: str) -> dict:
    logger.info("notification_delivery_job_started", notification_id=notification_id)
    return {"notification_id": notification_id, "delivered_channels": []}
