from app.models.model_registry import ModelRegistryEntry
from app.repositories.base import SQLAlchemyRepository


class ModelRepository(SQLAlchemyRepository[ModelRegistryEntry]):
    model = ModelRegistryEntry
