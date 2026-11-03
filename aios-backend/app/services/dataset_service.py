from app.application.services.base_service import BaseCRUDService
from app.models.dataset import DatasetModel
from app.repositories.dataset_repository import DatasetRepository


class DatasetService(BaseCRUDService[DatasetModel]):
    def __init__(self, repository: DatasetRepository):
        super().__init__(repository)
