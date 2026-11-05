"""Real concurrency stress tests: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every other AIOS
services. This platform has three commit-spanning-lock check-then-act
sequences (see each service's module docstring):
`GovernanceAssetService.register_asset` (idempotent-by-external-ref
creation), `ApprovalWorkflowService.record_decision` (approval-count
threshold crossing), and `SecretService.rotate_secret` (version
deactivate-then-create). Each test below proves the per-key
`asyncio.Lock` actually prevents the race a naive "check then write"
sequence would produce under real concurrency."""
from __future__ import annotations

import asyncio

import pytest

from security_platform.database.session import session_scope
from security_platform.governance.approval_service import ApprovalWorkflowService
from security_platform.governance.governance_service import GovernanceAssetService
from security_platform.models.governance import ApprovalPolicyModel
from security_platform.repositories.registry import RepositoryRegistry
from security_platform.secrets.secret_service import SecretService

TENANT = "stress-tenant"


async def _register_once(external_ref_id: str) -> str:
    # Never `return` from inside `async for session in session_scope():
    # ...` — that closes the generator via `GeneratorExit` without
    # resuming past the `yield`, silently skipping the post-yield
    # commit. Capture the result in an outer variable and return only
    # after the loop completes.
    asset_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = GovernanceAssetService(repos)
        asset = await service.register_asset(TENANT, asset_type="model", external_ref_id=external_ref_id, name="Stress Model")
        asset_id = asset.id
    return asset_id


@pytest.mark.asyncio
async def test_concurrent_asset_registration_does_not_duplicate():
    results = await asyncio.gather(*[_register_once("stress-model-1") for _ in range(15)])

    # Every concurrent caller should have been serialized onto the SAME
    # asset row (same id) rather than each creating its own — this is
    # exactly the bug an unlocked "check existing, then insert"
    # sequence would produce under real concurrency.
    assert len(set(results)) == 1

    matches = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        matches = await repos.governance_assets.list_by_lifecycle_stage(TENANT, "draft")
    assert sum(1 for a in matches if a.external_ref_id == "stress-model-1") == 1


async def _decide_once(request_id: str, approver_id: str) -> str:
    status = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = ApprovalWorkflowService(repos)
        request = await service.record_decision(TENANT, request_id, approver_id, "approve")
        status = request.status
    return status


@pytest.mark.asyncio
async def test_concurrent_approval_decisions_cross_threshold_exactly_once():
    n_approvers = 5
    asset_id = None
    request_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        await repos.approval_policies.add(
            ApprovalPolicyModel(tenant_id=TENANT, asset_type="workflow", required_approvals=n_approvers, approver_roles=["security_admin"])
        )
        gov = GovernanceAssetService(repos)
        approvals = ApprovalWorkflowService(repos)
        asset = await gov.register_asset(TENANT, asset_type="workflow", external_ref_id="stress-workflow-1", name="Stress Workflow")
        asset_id = asset.id
        request = await approvals.request_approval(TENANT, asset_id, asset_type="workflow", target_lifecycle_stage="approved")
        request_id = request.id

    final_statuses = await asyncio.gather(*[_decide_once(request_id, f"approver-{i}") for i in range(n_approvers)])

    # Every concurrent decision call serialized through the same lock,
    # so the LAST one processed should observe the crossed threshold —
    # exactly one of the returned statuses (whichever ran last) is
    # "approved"; without the lock, two decisions could both read the
    # same pre-crossing count and neither would flip to "approved".
    assert final_statuses.count("approved") == 1

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        request = await repos.approval_requests.get(request_id)
        decisions = await repos.approval_decisions.list_for_request(TENANT, request_id)
        asset = await repos.governance_assets.get(asset_id)
    assert request.status == "approved"
    assert len(decisions) == n_approvers  # no vote was lost to the race
    assert asset.lifecycle_stage == "approved"  # promoted exactly once


async def _rotate_once(secret_id: str, new_value: str) -> int:
    version_number = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = SecretService(repos)
        secret = await service.rotate_secret(TENANT, secret_id, new_value)
        version_number = secret.current_version_number
    return version_number


@pytest.mark.asyncio
async def test_concurrent_secret_rotations_never_collide_on_version_number():
    n_rotations = 10
    secret_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = SecretService(repos)
        secret = await service.create_secret(TENANT, name="stress-secret", secret_type="token", plaintext_value="v0")
        secret_id = secret.id

    await asyncio.gather(*[_rotate_once(secret_id, f"v{i + 1}") for i in range(n_rotations)])

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        secret = await repos.secrets.get(secret_id)
        versions = await repos.secret_versions.list_for_secret(TENANT, secret_id)

    version_numbers = [v.version_number for v in versions]
    assert len(version_numbers) == len(set(version_numbers))  # no two rotations landed on the same version_number
    assert secret.current_version_number == n_rotations + 1  # initial version + each rotation, serialized
    active_versions = [v for v in versions if v.is_active]
    assert len(active_versions) == 1  # exactly one version left active, never two
