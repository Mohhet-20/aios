from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin


class NotificationModel(IdMixin, AuditMixin, Base):
    __tablename__ = "notifications"

    recipient_user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notification_type: Mapped[str] = mapped_column(String(32), default="info", nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
