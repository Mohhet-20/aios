import pytest

from docs_platform.collaboration.review_service import ReviewService
from docs_platform.core.exceptions import ReviewAlreadyDecidedError, ValidationError

pytestmark = pytest.mark.asyncio

TENANT = "t-collab"


async def test_request_and_approve_review(repos):
    svc = ReviewService(repos)
    review = await svc.request_review(TENANT, "page-1", requested_by="author-1")
    assert review.status == "pending"

    decided = await svc.decide(TENANT, review.id, decision="approved", reviewer_id="reviewer-1", notes="looks good")
    assert decided.status == "approved"
    assert decided.decided_at is not None


async def test_cannot_decide_twice(repos):
    svc = ReviewService(repos)
    review = await svc.request_review(TENANT, "page-2", requested_by="author-1")
    await svc.decide(TENANT, review.id, decision="rejected", reviewer_id="reviewer-1")
    with pytest.raises(ReviewAlreadyDecidedError):
        await svc.decide(TENANT, review.id, decision="approved", reviewer_id="reviewer-2")


async def test_decide_rejects_unsupported_decision(repos):
    svc = ReviewService(repos)
    review = await svc.request_review(TENANT, "page-3", requested_by="author-1")
    with pytest.raises(ValidationError):
        await svc.decide(TENANT, review.id, decision="maybe", reviewer_id="reviewer-1")


async def test_list_for_page(repos):
    svc = ReviewService(repos)
    await svc.request_review(TENANT, "page-4", requested_by="author-1")
    await svc.request_review(TENANT, "page-4", requested_by="author-1")
    reviews = await svc.list_for_page(TENANT, "page-4")
    assert len(reviews) == 2
