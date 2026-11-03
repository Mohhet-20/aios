import pytest

from release_platform.core.exceptions import ConflictError, NotFoundError, ReleaseApprovalRequiredError, ValidationError
from release_platform.security.release_approval_service import ReleaseApprovalService

pytestmark = pytest.mark.asyncio

TENANT = "t-security"


async def test_request_and_decide_approval(repos):
    svc = ReleaseApprovalService(repos)
    approval = await svc.request_approval(TENANT, release_id="rel-1", approver_id="u1")
    assert approval.decision == "pending"

    decided = await svc.decide(TENANT, approval.id, decision="approved", notes="looks good")
    assert decided.decision == "approved"
    assert decided.decided_at is not None


async def test_cannot_decide_twice(repos):
    svc = ReleaseApprovalService(repos)
    approval = await svc.request_approval(TENANT, release_id="rel-2", approver_id="u1")
    await svc.decide(TENANT, approval.id, decision="rejected")
    with pytest.raises(ConflictError):
        await svc.decide(TENANT, approval.id, decision="approved")


async def test_decide_rejects_unsupported_decision(repos):
    svc = ReleaseApprovalService(repos)
    approval = await svc.request_approval(TENANT, release_id="rel-3", approver_id="u1")
    with pytest.raises(ValidationError):
        await svc.decide(TENANT, approval.id, decision="maybe")


async def test_get_or_404_raises_for_missing(repos):
    svc = ReleaseApprovalService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_assert_release_approved_raises_without_approval(repos):
    svc = ReleaseApprovalService(repos)
    with pytest.raises(ReleaseApprovalRequiredError):
        await svc.assert_release_approved(TENANT, "rel-unapproved")


async def test_assert_release_approved_passes_with_approval(repos):
    svc = ReleaseApprovalService(repos)
    approval = await svc.request_approval(TENANT, release_id="rel-4", approver_id="u1")
    await svc.decide(TENANT, approval.id, decision="approved")
    await svc.assert_release_approved(TENANT, "rel-4")


async def test_list_for_release(repos):
    svc = ReleaseApprovalService(repos)
    await svc.request_approval(TENANT, release_id="rel-5", approver_id="u1")
    await svc.request_approval(TENANT, release_id="rel-5", approver_id="u2")
    approvals = await svc.list_for_release(TENANT, "rel-5")
    assert len(approvals) == 2
