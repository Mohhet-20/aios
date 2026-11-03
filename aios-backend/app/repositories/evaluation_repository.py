from app.models.evaluation import EvaluationRunModel
from app.repositories.base import SQLAlchemyRepository


class EvaluationRepository(SQLAlchemyRepository[EvaluationRunModel]):
    model = EvaluationRunModel
