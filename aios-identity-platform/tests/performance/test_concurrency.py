"""Real concurrency/stress tests — genuinely independent sessions racing
against the same SQLite-file-backed database, not the single rollback-
isolated `repos` fixture every other test file uses. This is the same
kind of test that caught real lost-update races in sibling AIOS
platforms (e.g. the Evaluation Platform's dataset `item_count` bug in
Phase 10): a bug only shows up under real parallel writers, never
under sequential unit tests."""
from __future__ import annotations

import asyncio

import pytest

from identity_platform.config.settings import Settings
from identity_platform.core.exceptions import QuotaExceededError
from identity_platform.database.session import session_scope
from identity_platform.domain.enums import MembershipStatus, OrganizationStatus, UserStatus
from identity_platform.models.membership import OrganizationMembershipModel
from identity_platform.models.organization import OrganizationModel
from identity_platform.models.user import UserModel
from identity_platform.organizations.membership_service import MembershipService
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.sessions.session_service import SessionService


async def _setup_org_with_quota(*, seat_quota: int, name_suffix: str) -> tuple[str, list[str]]:
    """Creates an organization with a tight seat quota (owner already
    occupying one seat, matching `OrganizationService.create_organization`)
    and N candidate users to try to add as members concurrently.
    Returns (org_id, candidate_user_ids)."""
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        owner = await repos.users.add(UserModel(email=f"conc-owner-{name_suffix}@example.com", status=UserStatus.ACTIVE.value))
        org = await repos.organizations.add(OrganizationModel(
            name=f"Conc Co {name_suffix}", slug=f"conc-co-{name_suffix}", status=OrganizationStatus.ACTIVE.value,
            owner_user_id=owner.id, seat_quota=seat_quota, workspace_quota=10,
        ))
        org_id = org.id
        owner_id = owner.id

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        await repos.organization_memberships.add(OrganizationMembershipModel(
            organization_id=org_id, user_id=owner_id, status=MembershipStatus.ACTIVE.value,
        ))

    candidate_ids: list[str] = []
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        for i in range(10):
            user = await repos.users.add(UserModel(email=f"conc-candidate-{name_suffix}-{i}@example.com", status=UserStatus.ACTIVE.value))
            candidate_ids.append(user.id)

    return org_id, candidate_ids


@pytest.mark.asyncio
async def test_concurrent_seat_quota_never_oversold():
    """10 concurrent add-member attempts against an organization with a
    seat quota of 4 (1 already taken by the owner, so 3 more seats
    available) — no more than `seat_quota` active memberships should
    ever exist afterward, no matter how the attempts interleave."""
    org_id, candidate_ids = await _setup_org_with_quota(seat_quota=4, name_suffix="quota")

    async def try_add(user_id: str) -> str:
        # Must NOT `return` from inside the `async for` loop below — an
        # early return closes the underlying async generator via
        # `aclose()` instead of letting it run to natural exhaustion,
        # which skips `session_scope`'s post-yield `await session.commit()`
        # entirely. The result has to be captured in an outer variable
        # and returned only after the loop completes normally.
        outcome = "added"
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            service = MembershipService(repos)
            try:
                await service.add_organization_member(org_id, user_id)
            except QuotaExceededError:
                outcome = "rejected"
        return outcome

    results = await asyncio.gather(*[try_add(uid) for uid in candidate_ids])

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        members = await repos.organization_memberships.list_for_organization(org_id)
        active = [m for m in members if m.status == "active"]

    assert len(active) <= 4, (
        f"seat quota was oversold: {len(active)} active members against a quota of 4 "
        f"(results: {results.count('added')} added, {results.count('rejected')} rejected)"
    )


@pytest.mark.asyncio
async def test_concurrent_session_creation_respects_limit_or_evicts_cleanly():
    """8 concurrent session-creation calls for the same user, with a
    concurrent-session limit of 3 — every call should either succeed
    (evicting an older session) or fail cleanly; the final active-session
    count should never exceed the limit."""
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        user = await repos.users.add(UserModel(email="conc-session-user@example.com", status=UserStatus.ACTIVE.value))
        user_id = user.id

    settings = Settings(secret_key="x" * 32, max_concurrent_sessions_per_user=3)

    async def create_one() -> str:
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            service = SessionService(repos, settings=settings)
            await service.create_session(user_id)
        return "created"

    results = await asyncio.gather(*[create_one() for _ in range(8)], return_exceptions=True)
    failures = [r for r in results if isinstance(r, Exception)]
    assert not failures, f"unexpected exceptions during concurrent session creation: {failures}"

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        active = await repos.sessions.list_active_for_user(user_id)

    assert len(active) <= 3, f"concurrent session limit was exceeded: {len(active)} active sessions against a limit of 3"


@pytest.mark.asyncio
async def test_naive_check_then_insert_is_provably_unsafe_under_a_forced_race():
    """Demonstrates *why* `add_if_under_seat_quota` exists: this test
    deliberately reproduces the naive "count active members, then
    insert" pattern directly against the repository (bypassing the
    atomic guard), with every concurrent task's count-read forced to
    complete before any of them attempts to insert — the worst-case
    interleaving for a check-then-act race. This is a regression test
    for the *hazard*, not for production code (nothing in this
    codebase does a bare check-then-insert like this anymore)."""
    org_id, candidate_ids = await _setup_org_with_quota(seat_quota=2, name_suffix="naive-race")
    # quota=2, owner already occupies 1 seat -> exactly 1 seat "available"
    # per a stale read, but 5 tasks will all see that same stale read.
    contenders = candidate_ids[:5]

    ready = asyncio.Event()
    ready_count = 0
    lock = asyncio.Lock()

    async def try_add_naively(user_id: str) -> str:
        nonlocal ready_count
        outcome = "added"
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            org = await repos.organizations.get_or_404(org_id)
            members = await repos.organization_memberships.list_for_organization(org_id)
            active_count = sum(1 for m in members if m.status == "active")

            async with lock:
                ready_count += 1
                if ready_count == len(contenders):
                    ready.set()
            await ready.wait()  # every task's read has now happened before any write

            if active_count >= org.seat_quota:
                outcome = "rejected"
            else:
                await repos.organization_memberships.add(OrganizationMembershipModel(
                    organization_id=org_id, user_id=user_id, status=MembershipStatus.ACTIVE.value,
                ))
                outcome = "added"
        return outcome

    results = await asyncio.gather(*[try_add_naively(uid) for uid in contenders])

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        members = await repos.organization_memberships.list_for_organization(org_id)
        active = [m for m in members if m.status == "active"]

    # The naive pattern IS oversold under this forced interleaving —
    # that's the point of this test. If this assertion ever starts
    # failing (i.e. it stops overselling), the SQLite locking behavior
    # this test relies on to demonstrate the hazard has changed.
    assert len(active) > 2, (
        "expected the naive check-then-insert pattern to oversell the quota under a forced race "
        f"(got {len(active)} active members, results={results}) — if this no longer reproduces, "
        "the demonstration this test exists for is no longer valid and it should be revisited"
    )


@pytest.mark.asyncio
async def test_atomic_seat_quota_insert_is_safe_under_the_same_forced_race():
    """The fixed counterpart to the test above: same worst-case forced
    interleaving, but going through `add_if_under_seat_quota` (what
    `MembershipService.add_organization_member` actually calls) instead
    of a bare check-then-insert. The quota must never be oversold."""
    org_id, candidate_ids = await _setup_org_with_quota(seat_quota=2, name_suffix="atomic-race")
    contenders = candidate_ids[:5]

    ready = asyncio.Event()
    ready_count = 0
    lock = asyncio.Lock()

    async def try_add_atomically(user_id: str) -> str:
        nonlocal ready_count
        outcome = "added"
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            # Still read first, matching the same interleaving pressure
            # as the naive test above — the difference is entirely in
            # how the insert itself is performed.
            await repos.organizations.get_or_404(org_id)
            await repos.organization_memberships.list_for_organization(org_id)

            async with lock:
                ready_count += 1
                if ready_count == len(contenders):
                    ready.set()
            await ready.wait()

            membership = await repos.organization_memberships.add_if_under_seat_quota(org_id, user_id)
            outcome = "added" if membership is not None else "rejected"
        return outcome

    results = await asyncio.gather(*[try_add_atomically(uid) for uid in contenders])

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        members = await repos.organization_memberships.list_for_organization(org_id)
        active = [m for m in members if m.status == "active"]

    added = results.count("added")
    assert len(active) == 1 + added, "in-memory result count should match what's actually in the database"
    assert len(active) <= 2, (
        f"seat quota was oversold even through the atomic insert: {len(active)} active members against a quota of 2 "
        f"(per-task results: {results})"
    )
