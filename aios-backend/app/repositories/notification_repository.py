from app.models.notification import NotificationModel
from app.repositories.base import SQLAlchemyRepository


class NotificationRepository(SQLAlchemyRepository[NotificationModel]):
    model = NotificationModel

    async def list_for_user(self, user_id: str, unread_only: bool = False) -> list[NotificationModel]:
        filters = {"recipient_user_id": user_id}
        results = await self.list(**filters)
        if unread_only:
            results = [n for n in results if not n.read]
        return results
