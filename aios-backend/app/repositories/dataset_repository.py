from app.models.dataset import DatasetModel
from app.repositories.base import SQLAlchemyRepository


class DatasetRepository(SQLAlchemyRepository[DatasetModel]):
    model = DatasetModel
