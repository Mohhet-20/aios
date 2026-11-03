"""Pure-Python domain aggregates for Agent and Task, separate from their
ORM models — business rules (legal lifecycle transitions, subtask
creation) live here so they're testable without a database and reusable
from any service."""
from __future__ import annotations

from dataclasses import dataclass, field

from agent_platform.core.exceptions import InvalidTransitionError, ValidationError
from agent_platform.domain.enums import AgentHealthStatus, AgentLifecycleStatus, TaskPriority, TaskStatus


# -- Agent --------------------------------------------------------------------

_AGENT_STATUS_TRANSITIONS: dict[AgentLifecycleStatus, set[AgentLifecycleStatus]] = {
    AgentLifecycleStatus.DRAFT: {AgentLifecycleStatus.ACTIVE, AgentLifecycleStatus.ARCHIVED},
    AgentLifecycleStatus.ACTIVE: {AgentLifecycleStatus.PAUSED, AgentLifecycleStatus.DEPRECATED, AgentLifecycleStatus.ARCHIVED},
    AgentLifecycleStatus.PAUSED: {AgentLifecycleStatus.ACTIVE, AgentLifecycleStatus.DEPRECATED, AgentLifecycleStatus.ARCHIVED},
    AgentLifecycleStatus.DEPRECATED: {AgentLifecycleStatus.ARCHIVED},
    AgentLifecycleStatus.ARCHIVED: set(),
}


@dataclass
class Agent:
    id: str
    workspace_id: str
    agent_type_id: str
    name: str
    role: str
    instructions: str
    goals: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    resource_limits: dict = field(default_factory=dict)
    is_autonomous: bool = True
    status: AgentLifecycleStatus = AgentLifecycleStatus.DRAFT
    health_status: AgentHealthStatus = AgentHealthStatus.UNKNOWN
    version: int = 1

    def _transition(self, target: AgentLifecycleStatus) -> None:
        allowed = _AGENT_STATUS_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Agent '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def activate(self) -> None:
        self._transition(AgentLifecycleStatus.ACTIVE)

    def pause(self) -> None:
        self._transition(AgentLifecycleStatus.PAUSED)

    def resume(self) -> None:
        if self.status != AgentLifecycleStatus.PAUSED:
            raise InvalidTransitionError(f"Agent '{self.id}' is not paused (status: {self.status.value})")
        self._transition(AgentLifecycleStatus.ACTIVE)

    def deprecate(self) -> None:
        self._transition(AgentLifecycleStatus.DEPRECATED)

    def archive(self) -> None:
        self._transition(AgentLifecycleStatus.ARCHIVED)

    def update_health(self, health: AgentHealthStatus) -> None:
        self.health_status = health

    def is_executable(self) -> bool:
        """An agent can only be dispatched a task while ACTIVE and
        HEALTHY-or-DEGRADED — PAUSED/DEPRECATED/ARCHIVED/UNHEALTHY agents
        are excluded from task routing."""
        return self.status == AgentLifecycleStatus.ACTIVE and self.health_status != AgentHealthStatus.UNHEALTHY


# -- Task -----------------------------------------------------------------------

_TASK_STATUS_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.PLANNING, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.PLANNING: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.IN_PROGRESS: {TaskStatus.BLOCKED, TaskStatus.WAITING_APPROVAL, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.WAITING_APPROVAL: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},  # retry re-enters IN_PROGRESS
    TaskStatus.CANCELLED: set(),
}

_TERMINAL_STATUSES = {TaskStatus.COMPLETED, TaskStatus.CANCELLED}


@dataclass
class Task:
    id: str
    workspace_id: str
    title: str
    goal: str
    created_by: str
    parent_task_id: str | None = None
    root_task_id: str | None = None
    depth: int = 0
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_agent_id: str | None = None
    context: dict = field(default_factory=dict)
    result: dict | None = None
    confidence: float | None = None
    progress_percent: float = 0.0
    retry_count: int = 0
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.root_task_id is None:
            self.root_task_id = self.id

    def _transition(self, target: TaskStatus) -> None:
        allowed = _TASK_STATUS_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Task '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES

    def start_planning(self) -> None:
        self._transition(TaskStatus.PLANNING)

    def begin_execution(self, *, assigned_agent_id: str | None = None) -> None:
        self._transition(TaskStatus.IN_PROGRESS)
        if assigned_agent_id:
            self.assigned_agent_id = assigned_agent_id

    def block(self, reason: str) -> None:
        self._transition(TaskStatus.BLOCKED)
        self.failure_reason = reason

    def request_approval(self) -> None:
        self._transition(TaskStatus.WAITING_APPROVAL)

    def approve_and_resume(self) -> None:
        if self.status != TaskStatus.WAITING_APPROVAL:
            raise InvalidTransitionError(f"Task '{self.id}' is not waiting for approval (status: {self.status.value})")
        self._transition(TaskStatus.IN_PROGRESS)

    def complete(self, result: dict, *, confidence: float | None = None) -> None:
        self._transition(TaskStatus.COMPLETED)
        self.result = result
        self.confidence = confidence
        self.progress_percent = 100.0

    def fail(self, reason: str) -> None:
        self._transition(TaskStatus.FAILED)
        self.failure_reason = reason

    def cancel(self, reason: str | None = None) -> None:
        self._transition(TaskStatus.CANCELLED)
        if reason:
            self.failure_reason = reason

    def retry(self) -> None:
        if self.status != TaskStatus.FAILED:
            raise InvalidTransitionError(f"Task '{self.id}' can only be retried from FAILED (status: {self.status.value})")
        self._transition(TaskStatus.IN_PROGRESS)
        self.retry_count += 1
        self.failure_reason = None

    def update_progress(self, percent: float) -> None:
        if not 0.0 <= percent <= 100.0:
            raise ValidationError("progress_percent must be between 0 and 100")
        self.progress_percent = percent

    def new_subtask(self, *, id: str, title: str, goal: str, created_by: str, priority: TaskPriority = TaskPriority.NORMAL) -> "Task":
        """Pure decomposition: builds the child Task entity with depth/
        root linkage set correctly. Recursion-depth enforcement against
        `settings.max_agent_recursion_depth` happens in the planning
        service (which knows the configured limit); this method only
        guarantees the child's bookkeeping is internally consistent."""
        return Task(
            id=id, workspace_id=self.workspace_id, title=title, goal=goal, created_by=created_by,
            parent_task_id=self.id, root_task_id=self.root_task_id, depth=self.depth + 1, priority=priority,
        )
