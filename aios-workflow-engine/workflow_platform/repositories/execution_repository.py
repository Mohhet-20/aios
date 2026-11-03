from __future__ import annotations

from sqlalchemy import func, select

from workflow_platform.models.execution import ExecutionModel, NodeExecutionModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class ExecutionRepository(SQLAlchemyRepository[ExecutionModel]):
    model = ExecutionModel

    async def list_for_workflow(self, workflow_id: str, *, status: str | None = None, limit: int = 100) -> list[ExecutionModel]:
        stmt = select(ExecutionModel).where(ExecutionModel.workflow_id == workflow_id)
        if status:
            stmt = stmt.where(ExecutionModel.status == status)
        stmt = stmt.order_by(ExecutionModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None, limit: int = 200) -> list[ExecutionModel]:
        stmt = select(ExecutionModel).where(ExecutionModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(ExecutionModel.status == status)
        stmt = stmt.order_by(ExecutionModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_children(self, parent_execution_id: str) -> list[ExecutionModel]:
        stmt = select(ExecutionModel).where(ExecutionModel.parent_execution_id == parent_execution_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_active_for_workflow(self, workflow_id: str) -> int:
        stmt = select(func.count()).where(
            ExecutionModel.workflow_id == workflow_id,
            ExecutionModel.status.in_(["pending", "running", "paused", "waiting_approval", "compensating"]),
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_active_for_workspace(self, workspace_id: str) -> int:
        stmt = select(func.count()).where(
            ExecutionModel.workspace_id == workspace_id,
            ExecutionModel.status.in_(["pending", "running", "paused", "waiting_approval", "compensating"]),
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_by_status(self, status: str, *, limit: int = 500) -> list[ExecutionModel]:
        stmt = select(ExecutionModel).where(ExecutionModel.status == status).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_timed_out_candidates(self, *, as_of) -> list[ExecutionModel]:
        stmt = select(ExecutionModel).where(
            ExecutionModel.status == "running", ExecutionModel.timeout_at.is_not(None), ExecutionModel.timeout_at <= as_of,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class NodeExecutionRepository(SQLAlchemyRepository[NodeExecutionModel]):
    model = NodeExecutionModel

    async def list_for_execution(self, execution_id: str) -> list[NodeExecutionModel]:
        stmt = select(NodeExecutionModel).where(NodeExecutionModel.execution_id == execution_id).order_by(NodeExecutionModel.started_at)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest_for_node(self, execution_id: str, node_key: str) -> NodeExecutionModel | None:
        stmt = select(NodeExecutionModel).where(
            NodeExecutionModel.execution_id == execution_id, NodeExecutionModel.node_key == node_key,
        ).order_by(NodeExecutionModel.attempt_number.desc())
        return (await self.session.execute(stmt)).scalars().first()
