from app.models.experiment import ExperimentModel
from app.repositories.base import SQLAlchemyRepository


class ExperimentRepository(SQLAlchemyRepository[ExperimentModel]):
    model = ExperimentModel
