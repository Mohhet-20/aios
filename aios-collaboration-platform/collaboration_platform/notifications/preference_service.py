"""NotificationPreferenceService: per-user, per-notification-type
channel opt-in/opt-out. Absence of a stored row means "use the
platform default" (`in_app` always on, `email` on iff
`email_notifications_enabled_by_default`, `digest` off) rather than
silently doing nothing — a user who has never touched notification
settings still gets sensible defaults."""
from __future__ import annotations

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.models.notification import NotificationPreferenceModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class NotificationPreferenceService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def get_effective(self, user_id: str, notification_type: str) -> dict:
        pref = await self.repos.notification_preferences.get_for_user_and_type(user_id, notification_type)
        if pref is None:
            return {
                "in_app_enabled": True,
                "email_enabled": self.settings.email_notifications_enabled_by_default,
                "digest_enabled": False,
            }
        return {"in_app_enabled": pref.in_app_enabled, "email_enabled": pref.email_enabled, "digest_enabled": pref.digest_enabled}

    async def update_preference(
        self, user_id: str, notification_type: str, *, in_app_enabled: bool | None = None,
        email_enabled: bool | None = None, digest_enabled: bool | None = None,
    ) -> NotificationPreferenceModel:
        pref = await self.repos.notification_preferences.get_for_user_and_type(user_id, notification_type)
        if pref is None:
            defaults = await self.get_effective(user_id, notification_type)
            pref = NotificationPreferenceModel(user_id=user_id, notification_type=notification_type, **defaults)
            pref = await self.repos.notification_preferences.add(pref)
        if in_app_enabled is not None:
            pref.in_app_enabled = in_app_enabled
        if email_enabled is not None:
            pref.email_enabled = email_enabled
        if digest_enabled is not None:
            pref.digest_enabled = digest_enabled
        return await self.repos.notification_preferences.update(pref)

    async def list_for_user(self, user_id: str) -> list[NotificationPreferenceModel]:
        return await self.repos.notification_preferences.list_for_user(user_id)
