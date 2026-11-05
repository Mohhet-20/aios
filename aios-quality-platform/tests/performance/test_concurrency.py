"""Real concurrency stress tests: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every other AIOS
services. This platform has five commit-spanning-lock check-then-act
sequences: `TestSuiteService.register_suite` (get-or-create by name),
`BaselineService.set_baseline` (upsert by dimension+subject),
`SloService.register_slo` (get-or-create by name),
`QualityGateService.create_gate` (get-or-create by release+name), and
`FailurePatternService.record_occurrence` (get-or-increment by
pattern_type+subject_ref). Each test below proves the per-key
`asyncio.Lock` actually prevents the race a naive "check then write"
sequence would produce under real concurrency."""
from __future__ import annotations

import asyncio

import pytest

from quality_platform.ai_quality.baseline_service import BaselineService
from quality_platform.database.session import session_scope
from quality_platform.failure_analysis.failure_pattern_service import FailurePatternService
from quality_platform.quality_gates.quality_gate_service import QualityGateService
from quality_platform.reliability.slo_service import SloService
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.testing.test_suite_service import TestSuiteService

TENANT = "stress-tenant"


async def _register_suite_once() -> str:
    suite_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = TestSuiteService(repos)
        suite = await service.register_suite(TENANT, name="stress-suite", test_type="unit")
        suite_id = suite.id
    return suite_id


@pytest.mark.asyncio
async def test_concurrent_register_suite_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_suite_once() for _ in range(n_callers)])
    assert len(set(results)) == 1

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        suites = await repos.test_suites.list_for_tenant(TENANT)
    assert sum(1 for s in suites if s.name == "stress-suite") == 1


async def _set_baseline_once() -> str:
    baseline_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = BaselineService(repos)
        baseline = await service.set_baseline(TENANT, "groundedness", "agent:stress-1", baseline_score=90.0, sample_size=10)
        baseline_id = baseline.id
    return baseline_id


@pytest.mark.asyncio
async def test_concurrent_set_baseline_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_set_baseline_once() for _ in range(n_callers)])
    assert len(set(results)) == 1

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        baseline = await repos.ai_quality_baselines.get_for_subject(TENANT, "groundedness", "agent:stress-1")
    assert baseline is not None
    assert baseline.id == results[0]


async def _register_slo_once() -> str:
    slo_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = SloService(repos)
        slo = await service.register_slo(TENANT, name="stress-slo", service_ref="svc:stress-1")
        slo_id = slo.id
    return slo_id


@pytest.mark.asyncio
async def test_concurrent_register_slo_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_slo_once() for _ in range(n_callers)])
    assert len(set(results)) == 1

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        slos = await repos.slo_definitions.list_for_tenant(TENANT)
    assert sum(1 for s in slos if s.name == "stress-slo") == 1


async def _create_gate_once() -> str:
    gate_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = QualityGateService(repos)
        gate = await service.create_gate(TENANT, name="stress-gate", release_ref="rel:stress-1")
        gate_id = gate.id
    return gate_id


@pytest.mark.asyncio
async def test_concurrent_create_gate_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_create_gate_once() for _ in range(n_callers)])
    assert len(set(results)) == 1

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        gates = await repos.quality_gates.list_for_tenant(TENANT, release_ref="rel:stress-1")
    assert sum(1 for g in gates if g.name == "stress-gate") == 1


async def _record_occurrence_once() -> str:
    pattern_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = FailurePatternService(repos)
        pattern = await service.record_occurrence(TENANT, pattern_type="flaky_test", subject_ref="test:stress-1")
        pattern_id = pattern.id
    return pattern_id


@pytest.mark.asyncio
async def test_concurrent_record_occurrence_increments_without_losing_updates():
    n_callers = 15
    results = await asyncio.gather(*[_record_occurrence_once() for _ in range(n_callers)])

    # Every concurrent caller should have been serialized onto the SAME
    # pattern row (same id)...
    assert len(set(results)) == 1

    # ...and the occurrence counter should reflect all 15 increments,
    # not fewer — a naive unlocked read-increment-write sequence would
    # lose updates under real concurrency (two callers reading the same
    # starting count and both writing count+1).
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        pattern = await repos.failure_patterns.get_for_subject(TENANT, "flaky_test", "test:stress-1")
    assert pattern is not None
    assert pattern.occurrences == n_callers
