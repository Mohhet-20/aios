from app.application.services.base_service import BaseCRUDService
from app.models.experiment import ExperimentModel
from app.repositories.experiment_repository import ExperimentRepository


class ExperimentService(BaseCRUDService[ExperimentModel]):
    def __init__(self, repository: ExperimentRepository):
        super().__init__(repository)
