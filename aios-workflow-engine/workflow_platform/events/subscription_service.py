"""SubscriptionService: CRUD for `SubscriptionModel` — registering
interest (an internal handler or a webhook URL) in a given event type
within a workspace. Deliberately thin; `EventBus` is what actually
fans events out to whatever's subscribed."""
from __future__ import annotations

from workflow_platform.core.exceptions import ValidationError
from workflow_platform.domain.enums import SubscriptionTargetType
from workflow_platform.models.events import SubscriptionModel
from workflow_platform.repositories.registry import RepositoryRegistry


class SubscriptionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def subscribe_webhook(self, workspace_id: str, event_type: str, *, url: str, created_by: str, headers: dict | None = None) -> SubscriptionModel:
        if not url:
            raise ValidationError("a webhook subscription requires a 'url'")
        return await self.repos.subscriptions.add(SubscriptionModel(
            workspace_id=workspace_id, event_type=event_type, target_type=SubscriptionTargetType.WEBHOOK.value,
            target_config={"url": url, "headers": headers or {}}, created_by=created_by,
        ))

    async def subscribe_internal_handler(self, workspace_id: str, event_type: str, *, handler_key: str, created_by: str) -> SubscriptionModel:
        if not handler_key:
            raise ValidationError("an internal-handler subscription requires a 'handler_key'")
        return await self.repos.subscriptions.add(SubscriptionModel(
            workspace_id=workspace_id, event_type=event_type, target_type=SubscriptionTargetType.INTERNAL_HANDLER.value,
            target_config={"handler_key": handler_key}, created_by=created_by,
        ))

    async def list_for_workspace(self, workspace_id: str) -> list[SubscriptionModel]:
        return await self.repos.subscriptions.list_for_workspace(workspace_id)

    async def deactivate(self, subscription_id: str) -> SubscriptionModel:
        sub = await self.repos.subscriptions.get_or_404(subscription_id)
        sub.is_active = False
        return await self.repos.subscriptions.update(sub)

    async def reactivate(self, subscription_id: str) -> SubscriptionModel:
        sub = await self.repos.subscriptions.get_or_404(subscription_id)
        sub.is_active = True
        return await self.repos.subscriptions.update(sub)
