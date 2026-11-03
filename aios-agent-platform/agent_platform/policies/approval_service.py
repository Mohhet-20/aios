"""Approval gates: the human-in-the-loop checkpoint for non-autonomous
agents and sensitive tasks. Requesting approval moves the task into
IN_PROGRESS -> WAITING_APPROVAL (the state machine already models this
transition); approving resumes it to IN_PROGRESS via the same
`approve_and_resume` the domain entity exposes, rejecting fails it —
these are governance decisions surfaced as real task-lifecycle events,
not a side channel the task tree doesn't know about.
"""
from __future__ import annotations

from agent_platform.domain.enums import ApprovalStatus, TaskStatus
from agent_platform.models.governance import ApprovalGateModel
from agent_platform.models.task import TaskModel
from agent_platform.planner.mappers import apply_task_domain_to_model, task_to_domain
from agent_platform.repositories.registry import RepositoryRegistry
from agent_platform.clock import utc_now


class ApprovalService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def request_approval(self, task: TaskModel, *, reason: str, requested_by_agent_id: str | None = None, sensitivity_level: str = "normal") -> ApprovalGateModel:
        entity = task_to_domain(task)
        if entity.status == TaskStatus.PENDING:
            entity.start_planning()
        if entity.status == TaskStatus.PLANNING:
            entity.begin_execution()
        entity.request_approval()
        apply_task_domain_to_model(entity, task)
        await self.repos.tasks.update(task)

        return await self.repos.approval_gates.add(ApprovalGateModel(
            task_id=task.id, requested_by_agent_id=requested_by_agent_id, reason=reason, sensitivity_level=sensitivity_level,
        ))

    async def approve(self, gate_id: str, *, approver_id: str, notes: str | None = None) -> ApprovalGateModel:

        gate = await self.repos.approval_gates.get_or_404(gate_id)
        gate.status = ApprovalStatus.APPROVED.value
        gate.approver_id = approver_id
        gate.decision_notes = notes
        gate.resolved_at = utc_now()
        gate = await self.repos.approval_gates.update(gate)

        task = await self.repos.tasks.get_or_404(gate.task_id)
        entity = task_to_domain(task)
        entity.approve_and_resume()
        apply_task_domain_to_model(entity, task)
        await self.repos.tasks.update(task)
        return gate

    async def reject(self, gate_id: str, *, approver_id: str, notes: str | None = None) -> ApprovalGateModel:

        gate = await self.repos.approval_gates.get_or_404(gate_id)
        gate.status = ApprovalStatus.REJECTED.value
        gate.approver_id = approver_id
        gate.decision_notes = notes
        gate.resolved_at = utc_now()
        gate = await self.repos.approval_gates.update(gate)

        task = await self.repos.tasks.get_or_404(gate.task_id)
        entity = task_to_domain(task)
        entity.fail(f"approval rejected: {notes or 'no reason given'}")
        apply_task_domain_to_model(entity, task)
        await self.repos.tasks.update(task)
        return gate

    async def list_pending(self) -> list[ApprovalGateModel]:
        return await self.repos.approval_gates.list_pending()

    async def list_for_task(self, task_id: str) -> list[ApprovalGateModel]:
        return await self.repos.approval_gates.list_for_task(task_id)
