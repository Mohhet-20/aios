from sqlalchemy import select

from app.models.workflow import WorkflowExecutionModel, WorkflowModel
from app.repositories.base import SQLAlchemyRepository


class WorkflowRepository(SQLAlchemyRepository[WorkflowModel]):
    model = WorkflowModel


class WorkflowExecutionRepository(SQLAlchemyRepository[WorkflowExecutionModel]):
    model = WorkflowExecutionModel

    async def list_for_workflow(self, workflow_id: str, limit: int = 20) -> list[WorkflowExecutionModel]:
        result = await self.session.execute(
            select(WorkflowExecutionModel)
            .where(WorkflowExecutionModel.workflow_id == workflow_id)
            .order_by(WorkflowExecutionModel.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
