from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.user import UserModel
from identity_platform.repositories.base import SQLAlchemyRepository


class UserRepository(SQLAlchemyRepository[UserModel]):
    model = UserModel

    async def get_by_email(self, email: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.email == email.lower(), UserModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()
