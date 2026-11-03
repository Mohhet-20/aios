"""Notification creation/fan-out, preferences, read state, and digest
batching tests."""
from __future__ import annotations

import pytest

from collaboration_platform.domain.enums import DeliveryStatus, NotificationChannel, NotificationType
from collaboration_platform.notifications.delivery_service import NullEmailSender
from collaboration_platform.notifications.digest_service import DigestService
from collaboration_platform.notifications.notification_service import NotificationService
from collaboration_platform.notifications.preference_service import NotificationPreferenceService


@pytest.mark.asyncio
async def test_notify_fans_out_to_default_channels(repos):
    sender = NullEmailSender()
    svc = NotificationService(repos, email_sender=sender)
    notification = await svc.notify("user-1", NotificationType.MENTION, "You were mentioned", body="in a comment")

    deliveries = await repos.notification_deliveries.list_for_notification(notification.id)
    channels = {d.channel for d in deliveries}
    assert NotificationChannel.IN_APP.value in channels
    assert NotificationChannel.EMAIL.value in channels  # default-on
    assert NotificationChannel.DIGEST.value not in channels  # default-off
    email_delivery = next(d for d in deliveries if d.channel == NotificationChannel.EMAIL.value)
    assert email_delivery.status == DeliveryStatus.SENT.value
    assert len(sender.sent_log) == 1


@pytest.mark.asyncio
async def test_preferences_override_defaults(repos):
    pref_svc = NotificationPreferenceService(repos)
    await pref_svc.update_preference("user-2", NotificationType.MENTION.value, email_enabled=False, digest_enabled=True)

    svc = NotificationService(repos)
    notification = await svc.notify("user-2", NotificationType.MENTION, "Mentioned again")
    deliveries = await repos.notification_deliveries.list_for_notification(notification.id)
    channels = {d.channel for d in deliveries}
    assert NotificationChannel.EMAIL.value not in channels
    assert NotificationChannel.DIGEST.value in channels


@pytest.mark.asyncio
async def test_read_unread_state(repos):
    svc = NotificationService(repos)
    n1 = await svc.notify("user-3", NotificationType.ASSIGNMENT, "You were assigned a task")
    n2 = await svc.notify("user-3", NotificationType.PROJECT_UPDATE, "Project updated")

    assert await svc.count_unread("user-3") == 2
    await svc.mark_read(n1.id)
    assert await svc.count_unread("user-3") == 1
    unread = await svc.list_for_recipient("user-3", unread_only=True)
    assert len(unread) == 1 and unread[0].id == n2.id

    marked = await svc.mark_all_read("user-3")
    assert marked == 1
    assert await svc.count_unread("user-3") == 0


@pytest.mark.asyncio
async def test_digest_batches_pending_and_marks_delivered(repos):
    pref_svc = NotificationPreferenceService(repos)
    await pref_svc.update_preference("user-4", NotificationType.WORKFLOW_STATUS.value, in_app_enabled=False, email_enabled=False, digest_enabled=True)

    svc = NotificationService(repos)
    await svc.notify("user-4", NotificationType.WORKFLOW_STATUS, "Workflow A finished")
    await svc.notify("user-4", NotificationType.WORKFLOW_STATUS, "Workflow B finished")

    digest_svc = DigestService(repos)
    digest = await digest_svc.build_digest("user-4")
    assert digest is not None
    assert "2 update(s)" in digest.title
    assert "Workflow A finished" in digest.body
    assert "Workflow B finished" in digest.body

    # a second call with nothing new pending returns None
    again = await digest_svc.build_digest("user-4")
    assert again is None
