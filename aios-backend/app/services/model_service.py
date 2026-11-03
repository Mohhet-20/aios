from app.application.services.base_service import BaseCRUDService
from app.models.model_registry import ModelRegistryEntry
from app.repositories.model_repository import ModelRepository


class ModelService(BaseCRUDService[ModelRegistryEntry]):
    def __init__(self, repository: ModelRepository):
        super().__init__(repository)

    async def list_enabled(self) -> list[ModelRegistryEntry]:
        return await self.repository.list(is_enabled=True)
