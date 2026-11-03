from app.models.user import UserModel
from app.repositories.base import SQLAlchemyRepository


class UserRepository(SQLAlchemyRepository[UserModel]):
    model = UserModel

    async def get_by_email(self, email: str) -> UserModel | None:
        result = await self.session.execute(self._base_query().where(UserModel.email == email.lower()))
        return result.scalar_one_or_none()
