"""Real concurrency/stress tests — genuine independent DB
connections/transactions racing via `asyncio.gather`, not the
rollback-isolated `repos` fixture the rest of the suite uses. This
follows the exact methodology established across every other AIOS
services in this build (most recently the Identity Platform's
seat-quota and session-limit races): write the stress test first,
trust nothing about "it probably serializes fine," and fix whatever
genuine race the test proves exists.

Critical pitfall already learned the hard way in this build and
deliberately avoided here: never `return`/`break` from inside
`async for session in session_scope(): ...` — that closes the async
generator via `GeneratorExit` without resuming past the `yield`, so
the post-yield `await session.commit()` silently never runs and the
"test" ends up asserting against data that was never persisted.
Every helper below captures its result in an outer variable and lets
the loop finish naturally."""
from __future__ import annotations

import asyncio

import pytest

from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.config.settings import Settings
from collaboration_platform.database.session import session_scope
from collaboration_platform.domain.enums import AssetType
from collaboration_platform.realtime.edit_session_service import EditSessionService
from collaboration_platform.repositories.registry import RepositoryRegistry
from collaboration_platform.core.exceptions import ReviewAlreadyDecidedError
from collaboration_platform.reviews.review_service import ReviewService
from collaboration_platform.versioning.version_service import VersionService
from collaboration_platform.workspace.workspace_service import WorkspaceService


async def _make_asset(repos, name: str):
    ws = await WorkspaceService(repos).create_workspace(name=f"WS-{name}", owner_id="user-1")
    return await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.DOCUMENT, external_ref_id=f"ext-{name}", name=name, owner_id="user-1"
    )


@pytest.mark.asyncio
async def test_concurrent_edit_session_quota_never_oversold():
    """10 concurrent `start_session` calls for the same asset against a
    limit of 3 — the final active-editor count should never exceed the
    limit, even though every caller reads the count from its own
    independent transaction."""
    outcome: dict = {}
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        asset = await _make_asset(repos, "edit-quota")
        outcome["asset_id"] = asset.id

    asset_id = outcome["asset_id"]
    settings = Settings(secret_key="x" * 32, max_concurrent_editors_per_asset=3)

    async def start_one(user_id: str):
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            await EditSessionService(repos, settings=settings).start_session(asset_id, user_id)

    results = await asyncio.gather(*[start_one(f"user-{i}") for i in range(10)], return_exceptions=True)
    failures = [r for r in results if isinstance(r, Exception)]

    final = {}
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        active = await repos.edit_sessions.list_active_for_asset(asset_id)
        final["active_count"] = len(active)

    assert final["active_count"] <= 3, (
        f"concurrent edit-session quota was exceeded: {final['active_count']} active sessions against a limit of 3 "
        f"(gather returned {len(failures)} exceptions of {len(results)} calls)"
    )


@pytest.mark.asyncio
async def test_concurrent_version_creation_never_duplicates_version_numbers():
    """8 concurrent `create_version` calls for the same asset+branch —
    every version number must be unique and gapless from 1..N, proving
    `next_version_number`'s read-then-insert isn't silently losing or
    colliding numbers under real concurrency."""
    outcome: dict = {}
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        asset = await _make_asset(repos, "version-race")
        outcome["asset_id"] = asset.id

    asset_id = outcome["asset_id"]

    async def create_one(i: int):
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            await VersionService(repos).create_version(asset_id, f"user-{i}", {"n": i}, expected_base_version_id="__skip__")

    results = await asyncio.gather(*[create_one(i) for i in range(8)], return_exceptions=True)
    failures = [r for r in results if isinstance(r, Exception)]
    assert not failures, f"unexpected exceptions during concurrent version creation: {failures}"

    final = {}
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        versions = await repos.versions.list_for_asset(asset_id)
        final["numbers"] = sorted(v.version_number for v in versions)

    assert final["numbers"] == list(range(1, 9)), f"version numbers were not unique/gapless: {final['numbers']}"


@pytest.mark.asyncio
async def test_concurrent_review_approvals_reach_exact_threshold_not_more():
    """5 reviewers approve the same review request concurrently against
    a required_approvals=3 threshold. The correct outcome under real
    concurrency isn't "all 5 succeed" — once the 3rd approval lands the
    request is already decided, so the remaining 2 concurrent callers
    legitimately race to approve an already-decided request and should
    get a clean `ReviewAlreadyDecidedError`, not a silent no-op, a hang,
    or (the bug this test originally caught) a request stuck in
    IN_REVIEW forever despite enough approvals existing because every
    concurrent caller computed the threshold check from the same stale
    pre-approval count. The invariant that actually matters: the
    request ends up APPROVED, *exactly* `required_approvals` assignments
    are marked approved (never more — no overcounting), and every
    failure is the expected, meaningful `ReviewAlreadyDecidedError`
    rather than some other unexplained exception or data corruption."""
    outcome: dict = {}
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        asset = await _make_asset(repos, "review-race")
        review = await ReviewService(repos).request_review(
            asset.id, "user-1", reviewer_ids=[f"rev-{i}" for i in range(5)], required_approvals=3, sequential=False,
        )
        outcome["review_id"] = review.id

    review_id = outcome["review_id"]

    async def approve_one(reviewer_id: str):
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            await ReviewService(repos).approve(review_id, reviewer_id)

    results = await asyncio.gather(*[approve_one(f"rev-{i}") for i in range(5)], return_exceptions=True)
    failures = [r for r in results if isinstance(r, Exception)]
    unexpected_failures = [f for f in failures if not isinstance(f, ReviewAlreadyDecidedError)]
    assert not unexpected_failures, f"unexpected (non-ReviewAlreadyDecidedError) exceptions: {unexpected_failures}"

    final = {}
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        review = await repos.review_requests.get_or_404(review_id)
        assignments = await repos.review_assignments.list_for_request(review_id)
        final["status"] = review.status
        final["approved_count"] = sum(1 for a in assignments if a.status == "approved")
        final["pending_count"] = sum(1 for a in assignments if a.status == "pending")

    assert final["status"] == "approved", f"expected review to reach APPROVED, got {final['status']}"
    assert final["approved_count"] == 3, f"expected exactly 3 approved assignments (the threshold), got {final['approved_count']}"
    assert final["approved_count"] + final["pending_count"] == 5
    # the callers whose vote arrived after the decision was already made
    # should be exactly the ones that got ReviewAlreadyDecidedError
    assert len(failures) == 5 - final["approved_count"]
