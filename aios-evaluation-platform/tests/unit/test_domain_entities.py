import pytest

from eval_platform.core.exceptions import InvalidTransitionError, ValidationError
from eval_platform.domain.entities import Alert, BenchmarkRun, Dataset, Evaluation, EvaluationRun
from eval_platform.domain.enums import AlertStatus, DatasetStatus, EvaluationStatus, RunStatus


# -- Evaluation ----------------------------------------------------------------

def test_evaluation_activate_from_draft_sets_status_and_version():
    e = Evaluation(id="e1", workspace_id="w1", organization_id="o1", name="E", slug="e", owner_id="u1", category="prompt")
    e.activate("v1")
    assert e.status == EvaluationStatus.ACTIVE
    assert e.current_version_id == "v1"


def test_evaluation_activate_without_version_raises():
    e = Evaluation(id="e1", workspace_id="w1", organization_id="o1", name="E", slug="e", owner_id="u1", category="prompt")
    with pytest.raises(ValidationError):
        e.activate("")


def test_evaluation_activate_again_while_active_just_repoints_version():
    e = Evaluation(id="e1", workspace_id="w1", organization_id="o1", name="E", slug="e", owner_id="u1", category="prompt")
    e.activate("v1")
    e.activate("v2")
    assert e.status == EvaluationStatus.ACTIVE
    assert e.current_version_id == "v2"


def test_evaluation_deprecate_then_reactivate():
    e = Evaluation(id="e1", workspace_id="w1", organization_id="o1", name="E", slug="e", owner_id="u1", category="prompt")
    e.activate("v1")
    e.deprecate()
    assert e.status == EvaluationStatus.DEPRECATED
    e.activate("v2")
    assert e.status == EvaluationStatus.ACTIVE


def test_evaluation_archive_is_terminal():
    e = Evaluation(id="e1", workspace_id="w1", organization_id="o1", name="E", slug="e", owner_id="u1", category="prompt")
    e.archive()
    assert e.status == EvaluationStatus.ARCHIVED
    with pytest.raises(InvalidTransitionError):
        e.activate("v1")


# -- Dataset -------------------------------------------------------------------

def test_dataset_publish_and_republish():
    d = Dataset(id="d1", workspace_id="w1", organization_id="o1", name="D", slug="d", owner_id="u1", dataset_type="golden")
    d.publish("dv1")
    assert d.status == DatasetStatus.PUBLISHED
    d.republish("dv2")
    assert d.current_version_id == "dv2"
    assert d.status == DatasetStatus.PUBLISHED


def test_dataset_republish_before_publish_raises():
    d = Dataset(id="d1", workspace_id="w1", organization_id="o1", name="D", slug="d", owner_id="u1", dataset_type="golden")
    with pytest.raises(InvalidTransitionError):
        d.republish("dv1")


def test_dataset_archive_is_terminal():
    d = Dataset(id="d1", workspace_id="w1", organization_id="o1", name="D", slug="d", owner_id="u1", dataset_type="golden")
    d.publish("dv1")
    d.archive()
    assert d.status == DatasetStatus.ARCHIVED
    with pytest.raises(InvalidTransitionError):
        d.publish("dv2")


# -- EvaluationRun / BenchmarkRun (shared _RunMixin) ----------------------------

def test_evaluation_run_success_path_records_duration():
    r = EvaluationRun(id="r1", evaluation_id="e1", evaluation_version_id="v1", workspace_id="w1")
    r.start()
    assert r.status == RunStatus.RUNNING
    assert r.started_at is not None
    r.succeed()
    assert r.status == RunStatus.SUCCEEDED
    assert r.completed_at is not None
    assert r.duration_ms is not None and r.duration_ms >= 0


def test_evaluation_run_fail_then_retry_then_succeed():
    r = EvaluationRun(id="r1", evaluation_id="e1", evaluation_version_id="v1", workspace_id="w1", max_retries=1)
    r.start()
    r.fail("boom")
    assert r.status == RunStatus.FAILED
    r.retry()
    assert r.status == RunStatus.RUNNING
    assert r.attempt_number == 2
    r.succeed()
    assert r.status == RunStatus.SUCCEEDED


def test_evaluation_run_retry_exhausted_raises():
    r = EvaluationRun(id="r1", evaluation_id="e1", evaluation_version_id="v1", workspace_id="w1", max_retries=0)
    r.start()
    r.fail("boom")
    with pytest.raises(InvalidTransitionError):
        r.retry()


def test_evaluation_run_cancel_from_pending():
    r = EvaluationRun(id="r1", evaluation_id="e1", evaluation_version_id="v1", workspace_id="w1")
    r.cancel()
    assert r.status == RunStatus.CANCELLED
    assert r.completed_at is not None


def test_evaluation_run_timeout_sets_default_message():
    r = EvaluationRun(id="r1", evaluation_id="e1", evaluation_version_id="v1", workspace_id="w1")
    r.start()
    r.timeout()
    assert r.status == RunStatus.TIMED_OUT
    assert "timeout" in r.error_message


def test_evaluation_run_record_results_computes_failed_count():
    r = EvaluationRun(id="r1", evaluation_id="e1", evaluation_version_id="v1", workspace_id="w1")
    r.record_results(item_count=10, passed_count=7, overall_score=0.7, metric_summary={"accuracy": 0.7})
    assert r.failed_count == 3
    assert r.overall_score == 0.7


def test_benchmark_run_shares_same_state_machine():
    r = BenchmarkRun(id="br1", benchmark_id="b1", workspace_id="w1")
    r.start()
    r.succeed()
    assert r.status == RunStatus.SUCCEEDED


def test_run_cannot_transition_from_succeeded():
    r = EvaluationRun(id="r1", evaluation_id="e1", evaluation_version_id="v1", workspace_id="w1")
    r.start()
    r.succeed()
    with pytest.raises(InvalidTransitionError):
        r.start()


# -- Alert -----------------------------------------------------------------------

def test_alert_acknowledge_then_resolve():
    a = Alert(id="a1", workspace_id="w1", category="quality", severity="warning", message="score dropped")
    a.acknowledge(by="user-1")
    assert a.status == AlertStatus.ACKNOWLEDGED
    assert a.acknowledged_by == "user-1"
    a.resolve(by="user-2")
    assert a.status == AlertStatus.RESOLVED
    assert a.resolved_by == "user-2"


def test_alert_open_can_resolve_directly():
    a = Alert(id="a1", workspace_id="w1", category="cost", severity="critical", message="cost spike")
    a.resolve(by="user-1")
    assert a.status == AlertStatus.RESOLVED


def test_alert_reopen_clears_acknowledgement():
    a = Alert(id="a1", workspace_id="w1", category="cost", severity="critical", message="cost spike")
    a.acknowledge(by="user-1")
    a.reopen()
    assert a.status == AlertStatus.OPEN
    assert a.acknowledged_by is None


def test_alert_resolved_is_terminal():
    a = Alert(id="a1", workspace_id="w1", category="cost", severity="critical", message="cost spike")
    a.resolve(by="user-1")
    with pytest.raises(InvalidTransitionError):
        a.acknowledge(by="user-2")
