"""WorkflowService — orchestrates workflow execution using the
`WorkflowExecution` domain state machine, delegating the actual step-by-step
work to a background job (`app.workers.jobs.workflow_execution_job`) so
`POST /workflows/{id}/execute` returns immediately with a 202-style
execution handle rather than blocking the HTTP request for the workflow's
full duration — the "Long-running workflows" background-processing
requirement made concrete.
"""

from __future__ import annotations

from app.clock import utc_now
from app.core.time_utils import ensure_aware_utc
from app.domain.entities.workflow import WorkflowExecution as WorkflowExecutionEntity
from app.domain.events.events import WorkflowExecutionCompleted, WorkflowExecutionStarted
from app.domain.value_objects.enums import ExecutionStatus
from app.events.bus import EventBus
from app.models.workflow import WorkflowExecutionModel
from app.monitoring.metrics import WORKFLOW_EXECUTIONS
from app.repositories.workflow_repository import WorkflowExecutionRepository, WorkflowRepository
from app.workers.jobs.workflow_execution_job import run_workflow_execution
from app.workers.task_queue import TaskQueue


class WorkflowService:
    def __init__(
        self,
        workflows: WorkflowRepository,
        executions: WorkflowExecutionRepository,
        event_bus: EventBus,
        task_queue: TaskQueue,
    ):
        self.workflows = workflows
        self.executions = executions
        self.event_bus = event_bus
        self.task_queue = task_queue

    async def execute(
        self, workflow_id: str, input_payload: dict, triggered_by: str
    ) -> WorkflowExecutionModel:
        await self.workflows.get_or_404(workflow_id)

        execution_row = WorkflowExecutionModel(
            workflow_id=workflow_id,
            status=ExecutionStatus.PENDING.value,
            triggered_by=triggered_by,
            input_payload=input_payload,
            steps=[],
            started_at=utc_now(),
        )
        execution_row = await self.executions.add(execution_row)

        await self.event_bus.publish(
            WorkflowExecutionStarted(
                execution_id=execution_row.id, workflow_id=workflow_id, actor_id=triggered_by
            )
        )

        execution_row.status = ExecutionStatus.RUNNING.value
        await self.executions.update(execution_row)

        await self.task_queue.enqueue(
            f"workflow_execution:{execution_row.id}", run_workflow_execution, execution_row.id
        )

        return execution_row

    async def get_execution(self, execution_id: str) -> WorkflowExecutionModel:
        return await self.executions.get_or_404(execution_id)

    async def complete_execution(
        self, execution_id: str, success: bool, error: str | None = None
    ) -> WorkflowExecutionModel:
        """Called by the job runner (or, in tests, directly) once the
        workflow's steps have all resolved."""
        execution_row = await self.executions.get_or_404(execution_id)
        target = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED

        entity = WorkflowExecutionEntity(
            id=execution_row.id,
            workflow_id=execution_row.workflow_id,
            status=ExecutionStatus(execution_row.status),
            triggered_by=execution_row.triggered_by,
            input_payload=execution_row.input_payload,
            started_at=ensure_aware_utc(execution_row.started_at),
        )
        entity.transition(target)  # raises UnprocessableStateError if invalid from current status

        execution_row.status = entity.status.value
        execution_row.completed_at = entity.completed_at
        execution_row.error = error
        await self.executions.update(execution_row)

        WORKFLOW_EXECUTIONS.labels(workflow_id=execution_row.workflow_id, status=execution_row.status).inc()
        await self.event_bus.publish(
            WorkflowExecutionCompleted(
                execution_id=execution_id, workflow_id=execution_row.workflow_id, success=success
            )
        )
        return execution_row
