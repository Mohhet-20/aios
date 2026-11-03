import pytest

from docs_platform.core.exceptions import InvalidTransitionError, ValidationError
from docs_platform.learning.enrollment_service import EnrollmentService

pytestmark = pytest.mark.asyncio

TENANT = "t-learning"


async def test_enroll_requires_exactly_one_target(repos):
    svc = EnrollmentService(repos)
    with pytest.raises(ValidationError):
        await svc.enroll(TENANT, "u1")
    with pytest.raises(ValidationError):
        await svc.enroll(TENANT, "u1", tutorial_id="tut1", learning_path_id="path1")


async def test_enroll_is_idempotent_per_user_and_tutorial(repos):
    svc = EnrollmentService(repos)
    first = await svc.enroll(TENANT, "u1", tutorial_id="tut-idempotent")
    second = await svc.enroll(TENANT, "u1", tutorial_id="tut-idempotent")
    assert first.id == second.id


async def test_update_progress_auto_advances_and_completes(repos):
    svc = EnrollmentService(repos)
    enrollment = await svc.enroll(TENANT, "u2", tutorial_id="tut-progress")
    assert enrollment.status == "enrolled"

    mid = await svc.update_progress(TENANT, enrollment.id, progress_pct=50.0)
    assert mid.status == "in_progress"

    done = await svc.update_progress(TENANT, enrollment.id, progress_pct=100.0)
    assert done.status == "completed"
    assert done.completed_at is not None


async def test_update_progress_respects_custom_pass_threshold(repos):
    svc = EnrollmentService(repos)
    enrollment = await svc.enroll(TENANT, "u3", tutorial_id="tut-threshold")
    passed = await svc.update_progress(TENANT, enrollment.id, progress_pct=85.0, pass_threshold_pct=80.0)
    assert passed.status == "completed"


async def test_abandon_enrollment(repos):
    svc = EnrollmentService(repos)
    enrollment = await svc.enroll(TENANT, "u4", tutorial_id="tut-abandon")
    abandoned = await svc.abandon(TENANT, enrollment.id)
    assert abandoned.status == "abandoned"
    with pytest.raises(InvalidTransitionError):
        await svc.update_progress(TENANT, enrollment.id, progress_pct=10.0)


async def test_list_for_user(repos):
    svc = EnrollmentService(repos)
    await svc.enroll(TENANT, "u5", tutorial_id="tut-a")
    await svc.enroll(TENANT, "u5", learning_path_id="path-a")
    enrollments = await svc.list_for_user(TENANT, "u5")
    assert len(enrollments) == 2
