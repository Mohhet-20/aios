"""EvaluationService — Evaluation Engine gateway. Queues grading work as a
background job (real grading needs the AI Core; see
`app.workers.jobs.evaluation_job`) and exposes the regression-detection rule
via the `EvaluationRun` domain entity so "is this a regression" is computed
identically everywhere it's checked (API response, notification text,
promotion-gate check in `PromptService`).
"""

from __future__ import annotations

from app.domain.entities.evaluation import EvaluationRun as EvaluationRunEntity
from app.domain.events.events import EvaluationCompleted
from app.domain.value_objects.enums import EvaluationStatus
from app.events.bus import EventBus
from app.models.evaluation import EvaluationRunModel
from app.repositories.evaluation_repository import EvaluationRepository
from app.workers.jobs.evaluation_job import run_evaluation
from app.workers.task_queue import TaskQueue


class EvaluationService:
    def __init__(self, repository: EvaluationRepository, event_bus: EventBus, task_queue: TaskQueue):
        self.repository = repository
        self.event_bus = event_bus
        self.task_queue = task_queue

    async def run_suite(
        self, workspace_id: str, suite_name: str, target_type: str, target_id: str, dataset_id: str
    ) -> EvaluationRunModel:
        row = EvaluationRunModel(
            workspace_id=workspace_id,
            suite_name=suite_name,
            target_type=target_type,
            target_id=target_id,
            dataset_id=dataset_id,
            status=EvaluationStatus.QUEUED.value,
        )
        row = await self.repository.add(row)
        await self.task_queue.enqueue(f"evaluation:{row.id}", run_evaluation, row.id)
        return row

    async def complete_run(self, run_id: str, passed: int, failed: int) -> EvaluationRunModel:
        row = await self.repository.get_or_404(run_id)
        entity = EvaluationRunEntity(
            id=row.id,
            workspace_id=row.workspace_id,
            suite_name=row.suite_name,
            target_type=row.target_type,
            target_id=row.target_id,
            dataset_id=row.dataset_id,
            status=EvaluationStatus(row.status),
            previous_score=row.previous_score,
        )
        entity.complete(passed, failed)

        row.passed, row.failed, row.total, row.score, row.status = (
            entity.passed,
            entity.failed,
            entity.total,
            entity.score,
            entity.status.value,
        )
        await self.repository.update(row)

        await self.event_bus.publish(
            EvaluationCompleted(
                evaluation_run_id=run_id, score=entity.score or 0.0, passed=passed, failed=failed
            )
        )
        return row
