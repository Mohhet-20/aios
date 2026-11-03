"""Schema smoke test: every repository can round-trip a minimal row for
its model, and RepositoryRegistry memoizes one instance per repository."""
from __future__ import annotations

import datetime as dt

import pytest

from quality_platform.domain.enums import JobStatus, TestType
from quality_platform.models.ai_quality import AiQualityBaselineModel
from quality_platform.models.certification import CertificationRunModel
from quality_platform.models.chaos import ChaosExperimentModel
from quality_platform.models.failure_analysis import FailurePatternModel, RiskAssessmentModel
from quality_platform.models.observability import TrendSnapshotModel
from quality_platform.models.performance import PerformanceTestRunModel
from quality_platform.models.quality_gates import CoverageSnapshotModel, QualityGateModel
from quality_platform.models.reliability import ReliabilityMetricSnapshotModel, SloDefinitionModel
from quality_platform.models.security_testing import SecurityScanModel
from quality_platform.models.testing import TestRunModel, TestSuiteModel
from quality_platform.models.validation import ApiValidationRunModel, WorkflowValidationRunModel

pytestmark = pytest.mark.asyncio


async def test_registry_memoizes_repositories(repos):
    assert repos.test_suites is repos.test_suites
    assert repos.trend_snapshots is repos.trend_snapshots
    assert repos.test_suites is not repos.test_runs


async def test_test_suite_and_run_round_trip(repos):
    suite = await repos.test_suites.add(
        TestSuiteModel(tenant_id="t1", name="core-suite", test_type=TestType.UNIT.value, status="active")
    )
    await repos.session.commit()
    run = await repos.test_runs.add(
        TestRunModel(tenant_id="t1", suite_id=suite.id, status=JobStatus.QUEUED.value, triggered_by="ci")
    )
    await repos.session.commit()
    fetched = await repos.test_runs.get(run.id)
    assert fetched is not None
    assert fetched.suite_id == suite.id
    listed = await repos.test_runs.list_for_suite("t1", suite.id)
    assert len(listed) == 1


async def test_ai_quality_baseline_round_trip(repos):
    baseline = await repos.ai_quality_baselines.add(
        AiQualityBaselineModel(
            tenant_id="t1", dimension="groundedness", subject_ref="agent:1", baseline_score=90.0, sample_size=10
        )
    )
    await repos.session.commit()
    fetched = await repos.ai_quality_baselines.get_for_subject("t1", "groundedness", "agent:1")
    assert fetched is not None
    assert fetched.id == baseline.id


async def test_performance_and_chaos_round_trip(repos):
    perf = await repos.performance_test_runs.add(
        PerformanceTestRunModel(tenant_id="t1", performance_test_type="load", target_ref="svc:1", status=JobStatus.QUEUED.value)
    )
    chaos = await repos.chaos_experiments.add(
        ChaosExperimentModel(tenant_id="t1", failure_type="node_failure", target_ref="svc:1", status=JobStatus.QUEUED.value)
    )
    await repos.session.commit()
    assert (await repos.performance_test_runs.get(perf.id)) is not None
    assert (await repos.chaos_experiments.get(chaos.id)) is not None


async def test_security_and_validation_round_trip(repos):
    scan = await repos.security_scans.add(
        SecurityScanModel(tenant_id="t1", security_test_type="authentication", target_ref="svc:1", status=JobStatus.QUEUED.value)
    )
    api_val = await repos.api_validation_runs.add(
        ApiValidationRunModel(tenant_id="t1", validation_type="schema", target_ref="svc:1", outcome="passed")
    )
    wf_val = await repos.workflow_validation_runs.add(
        WorkflowValidationRunModel(tenant_id="t1", workflow_ref="wf:1", status=JobStatus.QUEUED.value)
    )
    await repos.session.commit()
    assert (await repos.security_scans.get(scan.id)) is not None
    assert (await repos.api_validation_runs.get(api_val.id)) is not None
    assert (await repos.workflow_validation_runs.get(wf_val.id)) is not None


async def test_reliability_and_quality_gates_round_trip(repos):
    slo = await repos.slo_definitions.add(
        SloDefinitionModel(tenant_id="t1", name="api-availability", service_ref="svc:1", target_pct=99.9, window_days=30)
    )
    snap = await repos.reliability_snapshots.add(
        ReliabilityMetricSnapshotModel(tenant_id="t1", service_ref="svc:1", metric_type="availability", value=99.95)
    )
    gate = await repos.quality_gates.add(
        QualityGateModel(tenant_id="t1", name="release-gate", release_ref="rel:1", min_score=80.0)
    )
    coverage = await repos.coverage_snapshots.add(
        CoverageSnapshotModel(tenant_id="t1", coverage_type="code", subject_ref="repo:1", covered_pct=85.0)
    )
    await repos.session.commit()
    assert (await repos.slo_definitions.get(slo.id)) is not None
    assert (await repos.reliability_snapshots.get(snap.id)) is not None
    assert (await repos.quality_gates.get(gate.id)) is not None
    assert (await repos.coverage_snapshots.get(coverage.id)) is not None


async def test_failure_risk_certification_observability_round_trip(repos):
    now = dt.datetime.now(dt.timezone.utc)
    pattern = await repos.failure_patterns.add(
        FailurePatternModel(
            tenant_id="t1", pattern_type="flaky_test", subject_ref="test:1", first_seen_at=now, last_seen_at=now
        )
    )
    risk = await repos.risk_assessments.add(
        RiskAssessmentModel(tenant_id="t1", subject_ref="rel:1", risk_score=42.0, risk_level="medium", assessed_at=now)
    )
    cert = await repos.certification_runs.add(
        CertificationRunModel(tenant_id="t1", release_ref="rel:1", status=JobStatus.QUEUED.value)
    )
    trend = await repos.trend_snapshots.add(
        TrendSnapshotModel(tenant_id="t1", metric_type="quality_score", value=88.0, recorded_at=now)
    )
    await repos.session.commit()
    assert (await repos.failure_patterns.get(pattern.id)) is not None
    assert (await repos.risk_assessments.get(risk.id)) is not None
    assert (await repos.certification_runs.get(cert.id)) is not None
    assert (await repos.trend_snapshots.get(trend.id)) is not None
