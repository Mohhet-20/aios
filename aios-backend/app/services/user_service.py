from app.application.services.base_service import BaseCRUDService
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository


class UserService(BaseCRUDService[UserModel]):
    def __init__(self, repository: UserRepository):
        super().__init__(repository)

    async def get_by_email(self, email: str) -> UserModel | None:
        return await self.repository.get_by_email(email)
