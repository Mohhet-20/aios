"""ReviewService: review requests + reviewer assignments, backed by
the guarded `ReviewRequest` domain entity for the pending -> in_review
-> approved/rejected/cancelled lifecycle. Sequential chains are
enforced here (a business rule about *whose turn it is*), while
"has this request crossed its required-approvals threshold" is the
entity's own job (`record_approval` returns whether the threshold was
just crossed) — the same split every guarded entity in this platform
follows: the entity owns its own state invariants, the service owns
everything that depends on other rows.

`approve`/`reject` read the current approved-count, mutate an
assignment row, and conditionally transition the request — a
check-then-act sequence spanning multiple statements. A stress test
proved this races under real concurrency: 5 reviewers approving
concurrently against a required_approvals=3 threshold all recorded
their individual approval, but every one of them computed the
threshold check from the *same stale pre-approval count* (each read
happened before any of the others had committed), so the request never
transitioned past IN_REVIEW even though enough approvals existed. Both
methods are now serialized per-review-request via an in-process
`asyncio.Lock` held across the read, the writes, *and* the commit —
the same fix (and the same reasoning: the lock must span the commit
because separate DB connections don't see each other's writes until
then) as the Identity Platform's `SessionService` and this platform's
own `EditSessionService.start_session`."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.core.exceptions import PermissionDeniedError, ReviewAlreadyDecidedError
from collaboration_platform.domain.entities import ReviewRequest
from collaboration_platform.domain.enums import ReviewAssignmentStatus, ReviewStatus
from collaboration_platform.models.review import ReviewAssignmentModel, ReviewRequestModel
from collaboration_platform.repositories.registry import RepositoryRegistry
from collaboration_platform.reviews.policy_service import ApprovalPolicyService


def _review_to_domain(model: ReviewRequestModel) -> ReviewRequest:
    return ReviewRequest(
        id=model.id, status=ReviewStatus(model.status), approvals_received=0,
        required_approvals=model.required_approvals, decided_at=model.decided_at,
    )


class ReviewService:
    # Per-review-request locks, shared across all ReviewService
    # instances within this process (keyed on review_request_id).
    _review_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.policies = ApprovalPolicyService(repos, settings=self.settings)

    async def request_review(
        self, asset_id: str, requested_by: str, reviewer_ids: list[str], *, version_id: str | None = None,
        title: str | None = None, description: str | None = None, sequential: bool | None = None,
        required_approvals: int | None = None,
    ) -> ReviewRequestModel:
        asset = await self.repos.assets.get_or_404(asset_id)
        policy = await self.policies.get_effective_policy(asset.workspace_id, asset.asset_type)

        effective_required = required_approvals or (policy.required_approvals if policy else self.settings.default_required_approvals)
        effective_required = min(effective_required, len(reviewer_ids)) if reviewer_ids else effective_required
        effective_sequential = sequential if sequential is not None else (policy.sequential if policy else False)

        review = await self.repos.review_requests.add(ReviewRequestModel(
            asset_id=asset_id, version_id=version_id, policy_id=policy.id if policy else None,
            requested_by=requested_by, title=title, description=description, required_approvals=effective_required,
        ))
        for order, reviewer_id in enumerate(reviewer_ids):
            await self.repos.review_assignments.add(ReviewAssignmentModel(
                review_request_id=review.id, reviewer_id=reviewer_id,
                sequence_order=order if effective_sequential else 0,
            ))
        return review

    async def _assert_reviewer_turn(self, review: ReviewRequestModel, assignment: ReviewAssignmentModel) -> None:
        """Only meaningful for sequential chains (sequence_order > 0
        possible): every assignment with a lower sequence_order must
        already be decided before this one can act."""
        all_assignments = await self.repos.review_assignments.list_for_request(review.id)
        for other in all_assignments:
            if other.sequence_order < assignment.sequence_order and other.status == ReviewAssignmentStatus.PENDING.value:
                raise PermissionDeniedError(
                    f"reviewer '{assignment.reviewer_id}' cannot act yet — reviewer '{other.reviewer_id}' "
                    f"(sequence {other.sequence_order}) has not yet decided"
                )

    async def approve(self, review_request_id: str, reviewer_id: str, *, comment: str | None = None) -> ReviewRequestModel:
        from collaboration_platform.database.base import utcnow
        async with self._review_locks[review_request_id]:
            review = await self.repos.review_requests.get_or_404(review_request_id)
            assignment = await self._get_pending_assignment(review_request_id, reviewer_id)
            await self._assert_reviewer_turn(review, assignment)

            # Count approvals *before* this one lands, since `approvals_received`
            # isn't a persisted column (deliberately — see ReviewRequestModel's
            # docstring precedent on never caching what can be recomputed) and
            # the entity's own `record_approval()` does its own +1 internally;
            # seeding it with the pre-approval count and calling it once keeps
            # the entity as the single source of truth for the threshold check
            # instead of double-counting this approval. Holding the lock across
            # this read is what makes the count trustworthy under concurrency —
            # see the class docstring for the race this fixes.
            prior_approved_count = await self._count_approved(review_request_id)

            assignment.status = ReviewAssignmentStatus.APPROVED.value
            assignment.comment = comment
            assignment.decided_at = utcnow()
            await self.repos.review_assignments.update(assignment)

            entity = _review_to_domain(review)
            entity.approvals_received = prior_approved_count
            entity.record_approval()
            review.status = entity.status.value
            review.decided_at = entity.decided_at
            updated = await self.repos.review_requests.update(review)
            await self.repos.session.commit()
        return updated

    async def reject(self, review_request_id: str, reviewer_id: str, *, comment: str | None = None) -> ReviewRequestModel:
        from collaboration_platform.database.base import utcnow
        async with self._review_locks[review_request_id]:
            review = await self.repos.review_requests.get_or_404(review_request_id)
            assignment = await self._get_pending_assignment(review_request_id, reviewer_id)
            await self._assert_reviewer_turn(review, assignment)

            assignment.status = ReviewAssignmentStatus.REJECTED.value
            assignment.comment = comment
            assignment.decided_at = utcnow()
            await self.repos.review_assignments.update(assignment)

            entity = _review_to_domain(review)
            entity.reject()
            review.status = entity.status.value
            review.decided_at = entity.decided_at
            updated = await self.repos.review_requests.update(review)
            await self.repos.session.commit()
        return updated

    async def cancel(self, review_request_id: str) -> ReviewRequestModel:
        review = await self.repos.review_requests.get_or_404(review_request_id)
        entity = _review_to_domain(review)
        entity.cancel()
        review.status = entity.status.value
        review.decided_at = entity.decided_at
        return await self.repos.review_requests.update(review)

    async def _get_pending_assignment(self, review_request_id: str, reviewer_id: str) -> ReviewAssignmentModel:
        assignments = await self.repos.review_assignments.list_for_request(review_request_id)
        for assignment in assignments:
            if assignment.reviewer_id == reviewer_id:
                if assignment.status != ReviewAssignmentStatus.PENDING.value:
                    raise ReviewAlreadyDecidedError(f"reviewer '{reviewer_id}' has already decided ({assignment.status})")
                return assignment
        raise PermissionDeniedError(f"user '{reviewer_id}' is not an assigned reviewer for request '{review_request_id}'")

    async def _count_approved(self, review_request_id: str) -> int:
        assignments = await self.repos.review_assignments.list_for_request(review_request_id)
        return sum(1 for a in assignments if a.status == ReviewAssignmentStatus.APPROVED.value)

    async def list_for_asset(self, asset_id: str) -> list[ReviewRequestModel]:
        return await self.repos.review_requests.list_for_asset(asset_id)

    async def list_assignments(self, review_request_id: str) -> list[ReviewAssignmentModel]:
        return await self.repos.review_assignments.list_for_request(review_request_id)

    async def list_for_reviewer(self, reviewer_id: str, *, pending_only: bool = False) -> list[ReviewAssignmentModel]:
        return await self.repos.review_assignments.list_for_reviewer(reviewer_id, pending_only=pending_only)
