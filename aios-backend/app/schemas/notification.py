from datetime import datetime

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: str
    recipient_user_id: str
    title: str
    description: str
    notification_type: str
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
