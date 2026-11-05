"""Real concurrency stress tests: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every other AIOS
services. This platform has three commit-spanning-lock check-then-act
sequences (see each service's module docstring):
`K8sResourceService.apply_resource` (upsert-by-identity creation),
`DeploymentGateService.approve` (approval-count threshold crossing),
and `ScalingPolicyService.evaluate_scale` (cooldown-checked event
creation). Each test below proves the per-key `asyncio.Lock` actually
prevents the race a naive "check then write" sequence would produce
under real concurrency."""
from __future__ import annotations

import asyncio

import pytest

from infra_platform.autoscaling.autoscaling_service import ScalingPolicyService
from infra_platform.cicd.cicd_service import DeploymentGateService
from infra_platform.core.exceptions import AutoscalingError
from infra_platform.database.session import session_scope
from infra_platform.kubernetes.k8s_service import ClusterService, K8sResourceService
from infra_platform.repositories.registry import RepositoryRegistry

TENANT = "stress-tenant"


async def _apply_once(cluster_id: str) -> str:
    # Never `return` from inside `async for session in session_scope():
    # ...` — that closes the generator via `GeneratorExit` without
    # resuming past the `yield`, silently skipping the post-yield
    # commit. Capture the result in an outer variable and return only
    # after the loop completes.
    resource_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = K8sResourceService(repos)
        resource = await service.apply_resource(
            TENANT, cluster_id, namespace="default", kind="deployment", name="stress-api", spec={"image": "aios/api:1.0.0"}
        )
        resource_id = resource.id
    return resource_id


@pytest.mark.asyncio
async def test_concurrent_apply_resource_does_not_duplicate():
    cluster_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        cluster_service = ClusterService(repos)
        cluster = await cluster_service.create_cluster(TENANT, name="stress-cluster", provider="aws", region="us-east-1")
        cluster = await cluster_service.mark_healthy(TENANT, cluster.id)
        cluster_id = cluster.id

    results = await asyncio.gather(*[_apply_once(cluster_id) for _ in range(15)])

    # Every concurrent caller should have been serialized onto the SAME
    # resource row (same id) rather than each creating its own — this
    # is exactly the bug an unlocked "check existing, then insert"
    # sequence would produce under real concurrency.
    assert len(set(results)) == 1

    resources = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        resources = await repos.k8s_resources.list_for_namespace(TENANT, cluster_id, "default")
    assert sum(1 for r in resources if r.kind == "deployment" and r.name == "stress-api") == 1


async def _approve_once(gate_id: str) -> str:
    status = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = DeploymentGateService(repos)
        gate = await service.approve(TENANT, gate_id)
        status = gate.status
    return status


@pytest.mark.asyncio
async def test_concurrent_gate_approvals_cross_threshold_exactly_once():
    n_approvers = 6
    gate_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = DeploymentGateService(repos)
        gate = await service.create_gate(TENANT, "stress-run-1", name="stress-gate", required_approvals=n_approvers)
        gate_id = gate.id

    final_statuses = await asyncio.gather(*[_approve_once(gate_id) for _ in range(n_approvers)])

    # Every concurrent approval serialized through the same lock, so
    # only the LAST one processed observes the crossed threshold —
    # exactly one of the returned statuses is "approved"; without the
    # lock, two approvals could both read the same pre-crossing count
    # and neither (or both, inconsistently) would flip to "approved".
    assert final_statuses.count("approved") == 1

    gate = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        gate = await repos.deployment_gates.get(gate_id)
    assert gate.status == "approved"
    assert gate.approvals_received == n_approvers  # no vote was lost to the race


async def _evaluate_once(policy_id: str, desired: int) -> object:
    event = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = ScalingPolicyService(repos)
        event = await service.evaluate_scale(TENANT, policy_id, current_capacity=2, desired_capacity=desired)
    return event


@pytest.mark.asyncio
async def test_concurrent_scale_evaluations_respect_cooldown():
    from infra_platform.config.settings import Settings

    policy_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = ScalingPolicyService(repos, settings=Settings(scale_up_cooldown_seconds=60, scale_down_cooldown_seconds=60))
        policy = await service.create_policy(
            TENANT, resource_type="node_pool", resource_id="stress-pool", policy_type="horizontal", min_capacity=1, max_capacity=20
        )
        policy_id = policy.id

    n_callers = 8
    results = await asyncio.gather(*[_evaluate_once(policy_id, 5 + i) for i in range(n_callers)], return_exceptions=True)

    succeeded = [r for r in results if not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, Exception)]

    # Only the first evaluation to acquire the lock should have gone
    # through; every other concurrent caller must observe the
    # now-committed scaling event and hit the cooldown, proving the
    # lock closed the window a naive "read last event, then insert"
    # sequence would otherwise leave open.
    assert len(succeeded) == 1
    assert len(failed) == n_callers - 1
    assert all(isinstance(exc, AutoscalingError) for exc in failed)

    events = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        events = await repos.scaling_events.list_for_policy(TENANT, policy_id)
    assert len(events) == 1  # exactly one scaling event was ever recorded
