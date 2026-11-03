import pytest

from agent_platform.core.exceptions import InvalidTransitionError, ValidationError
from agent_platform.domain.dependency_graph import validate_no_cycle, would_create_cycle
from agent_platform.domain.entities import Agent, Task
from agent_platform.domain.enums import AgentHealthStatus, AgentLifecycleStatus, TaskPriority, TaskStatus


def make_agent(**overrides) -> Agent:
    defaults = dict(id="a1", workspace_id="w1", agent_type_id="t1", name="Planner", role="Planner", instructions="Plan things.")
    defaults.update(overrides)
    return Agent(**defaults)


def make_task(**overrides) -> Task:
    defaults = dict(id="task1", workspace_id="w1", title="Do the thing", goal="Do the thing well", created_by="u1")
    defaults.update(overrides)
    return Task(**defaults)


# -- Agent lifecycle --------------------------------------------------------

def test_agent_full_lifecycle_happy_path():
    agent = make_agent()
    assert agent.status == AgentLifecycleStatus.DRAFT
    agent.activate()
    assert agent.status == AgentLifecycleStatus.ACTIVE
    agent.pause()
    assert agent.status == AgentLifecycleStatus.PAUSED
    agent.resume()
    assert agent.status == AgentLifecycleStatus.ACTIVE
    agent.deprecate()
    assert agent.status == AgentLifecycleStatus.DEPRECATED
    agent.archive()
    assert agent.status == AgentLifecycleStatus.ARCHIVED


def test_agent_archived_is_terminal():
    agent = make_agent(status=AgentLifecycleStatus.ARCHIVED)
    with pytest.raises(InvalidTransitionError):
        agent.activate()


def test_agent_cannot_resume_when_not_paused():
    agent = make_agent(status=AgentLifecycleStatus.ACTIVE)
    with pytest.raises(InvalidTransitionError):
        agent.resume()


def test_agent_draft_cannot_pause_directly():
    agent = make_agent()
    with pytest.raises(InvalidTransitionError):
        agent.pause()


def test_agent_is_executable_only_when_active_and_not_unhealthy():
    agent = make_agent()
    assert agent.is_executable() is False  # still DRAFT
    agent.activate()
    assert agent.is_executable() is True
    agent.update_health(AgentHealthStatus.DEGRADED)
    assert agent.is_executable() is True  # degraded still allowed
    agent.update_health(AgentHealthStatus.UNHEALTHY)
    assert agent.is_executable() is False
    agent.update_health(AgentHealthStatus.HEALTHY)
    agent.pause()
    assert agent.is_executable() is False  # paused blocks dispatch regardless of health


# -- Task lifecycle -----------------------------------------------------------

def test_task_root_task_id_defaults_to_self():
    task = make_task()
    assert task.root_task_id == task.id
    assert task.depth == 0


def test_task_full_lifecycle_happy_path():
    task = make_task()
    task.start_planning()
    assert task.status == TaskStatus.PLANNING
    task.begin_execution(assigned_agent_id="a1")
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.assigned_agent_id == "a1"
    task.complete({"answer": "42"}, confidence=0.9)
    assert task.status == TaskStatus.COMPLETED
    assert task.result == {"answer": "42"}
    assert task.progress_percent == 100.0
    assert task.is_terminal() is True


def test_task_block_and_resume():
    task = make_task()
    task.begin_execution()
    task.block("waiting on external data")
    assert task.status == TaskStatus.BLOCKED
    assert task.failure_reason == "waiting on external data"
    task.begin_execution()
    assert task.status == TaskStatus.IN_PROGRESS


def test_task_approval_flow():
    task = make_task()
    task.begin_execution()
    task.request_approval()
    assert task.status == TaskStatus.WAITING_APPROVAL
    task.approve_and_resume()
    assert task.status == TaskStatus.IN_PROGRESS


def test_task_approve_and_resume_requires_waiting_status():
    task = make_task()
    with pytest.raises(InvalidTransitionError):
        task.approve_and_resume()


def test_task_fail_and_retry():
    task = make_task()
    task.begin_execution()
    task.fail("model timeout")
    assert task.status == TaskStatus.FAILED
    assert task.retry_count == 0
    task.retry()
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.retry_count == 1
    assert task.failure_reason is None


def test_task_retry_only_allowed_from_failed():
    task = make_task()
    with pytest.raises(InvalidTransitionError):
        task.retry()


def test_task_cancel_from_pending():
    task = make_task()
    task.cancel("no longer needed")
    assert task.status == TaskStatus.CANCELLED
    assert task.is_terminal() is True


def test_task_completed_is_terminal_and_immutable_transition():
    task = make_task()
    task.begin_execution()
    task.complete({"ok": True})
    with pytest.raises(InvalidTransitionError):
        task.fail("too late")


def test_task_update_progress_validates_range():
    task = make_task()
    task.update_progress(50.0)
    assert task.progress_percent == 50.0
    with pytest.raises(ValidationError):
        task.update_progress(150.0)


def test_task_new_subtask_links_depth_and_root():
    root = make_task(id="root")
    child = root.new_subtask(id="child1", title="Sub", goal="Do part", created_by="u1")
    assert child.parent_task_id == "root"
    assert child.root_task_id == "root"
    assert child.depth == 1

    grandchild = child.new_subtask(id="grandchild1", title="Sub-sub", goal="Do part of part", created_by="u1")
    assert grandchild.root_task_id == "root"
    assert grandchild.depth == 2


def test_task_new_subtask_inherits_priority_default_and_override():
    root = make_task()
    child = root.new_subtask(id="c1", title="x", goal="y", created_by="u1", priority=TaskPriority.CRITICAL)
    assert child.priority == TaskPriority.CRITICAL


# -- dependency graph -----------------------------------------------------------

def test_no_cycle_for_independent_edges():
    edges = [("t2", "t1")]
    assert would_create_cycle(edges, ("t3", "t2")) is False
    validate_no_cycle(edges, ("t3", "t2"))  # should not raise


def test_direct_cycle_detected():
    edges = [("t1", "t2")]
    assert would_create_cycle(edges, ("t2", "t1")) is True


def test_self_dependency_is_a_cycle():
    assert would_create_cycle([], ("t1", "t1")) is True


def test_transitive_cycle_detected():
    edges = [("t1", "t2"), ("t2", "t3")]
    assert would_create_cycle(edges, ("t3", "t1")) is True
