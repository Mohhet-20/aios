"""Collaboration: page review requests. Status is a simple field
guarded directly here — pending -> approved/changes_requested/rejected
is a one-shot decision with no further transitions, so a dedicated
domain entity would add no value over a direct guard, the same
"simple status field" precedent used throughout this platform family.
Deciding an already-decided review raises `ReviewAlreadyDecidedError`
rather than the generic `InvalidTransitionError`, since "someone else
already reviewed this" is a meaningfully different situation for a
caller to handle than a generic bad state transition."""
from __future__ import annotations


from docs_platform.core.exceptions import ReviewAlreadyDecidedError, ReviewNotFoundError, ValidationError
from docs_platform.domain.enums import ReviewStatus
from docs_platform.models.collaboration import ReviewModel
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.clock import utc_now

_DECISION_STATUSES = {ReviewStatus.APPROVED.value, ReviewStatus.CHANGES_REQUESTED.value, ReviewStatus.REJECTED.value}


class ReviewService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_or_404(self, tenant_id: str, review_id: str) -> ReviewModel:
        review = await self.repos.reviews.get_or_404(review_id)
        if review.tenant_id != tenant_id:
            raise ReviewNotFoundError(f"Review '{review_id}' not found for tenant '{tenant_id}'")
        return review

    async def request_review(self, tenant_id: str, page_id: str, *, requested_by: str, reviewer_id: str | None = None) -> ReviewModel:
        review = ReviewModel(
            tenant_id=tenant_id, page_id=page_id, requested_by=requested_by,
            reviewer_id=reviewer_id, status=ReviewStatus.PENDING.value,
        )
        return await self.repos.reviews.add(review)

    async def decide(self, tenant_id: str, review_id: str, *, decision: str, reviewer_id: str, notes: str = "") -> ReviewModel:
        if decision not in _DECISION_STATUSES:
            raise ValidationError(f"Unsupported review decision '{decision}'")
        review = await self.get_or_404(tenant_id, review_id)
        if review.status != ReviewStatus.PENDING.value:
            raise ReviewAlreadyDecidedError(f"Review '{review_id}' was already decided ('{review.status}')")
        review.status = decision
        review.reviewer_id = reviewer_id
        review.notes = notes
        review.decided_at = utc_now()
        return await self.repos.reviews.update(review)

    async def list_for_page(self, tenant_id: str, page_id: str) -> list[ReviewModel]:
        return await self.repos.reviews.list_for_page(tenant_id, page_id)
