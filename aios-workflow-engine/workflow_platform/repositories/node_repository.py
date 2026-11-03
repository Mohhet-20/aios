from __future__ import annotations

from sqlalchemy import select

from workflow_platform.models.node import WorkflowEdgeModel, WorkflowNodeModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class WorkflowNodeRepository(SQLAlchemyRepository[WorkflowNodeModel]):
    model = WorkflowNodeModel

    async def list_for_version(self, workflow_version_id: str) -> list[WorkflowNodeModel]:
        stmt = select(WorkflowNodeModel).where(WorkflowNodeModel.workflow_version_id == workflow_version_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_key(self, workflow_version_id: str, node_key: str) -> WorkflowNodeModel | None:
        stmt = select(WorkflowNodeModel).where(WorkflowNodeModel.workflow_version_id == workflow_version_id, WorkflowNodeModel.node_key == node_key)
        return (await self.session.execute(stmt)).scalars().first()


class WorkflowEdgeRepository(SQLAlchemyRepository[WorkflowEdgeModel]):
    model = WorkflowEdgeModel

    async def list_for_version(self, workflow_version_id: str) -> list[WorkflowEdgeModel]:
        stmt = select(WorkflowEdgeModel).where(WorkflowEdgeModel.workflow_version_id == workflow_version_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_outgoing(self, workflow_version_id: str, node_key: str) -> list[WorkflowEdgeModel]:
        stmt = select(WorkflowEdgeModel).where(WorkflowEdgeModel.workflow_version_id == workflow_version_id, WorkflowEdgeModel.source_node_key == node_key)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_incoming(self, workflow_version_id: str, node_key: str) -> list[WorkflowEdgeModel]:
        stmt = select(WorkflowEdgeModel).where(WorkflowEdgeModel.workflow_version_id == workflow_version_id, WorkflowEdgeModel.target_node_key == node_key)
        return list((await self.session.execute(stmt)).scalars().all())
