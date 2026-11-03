"""Learning Platform: enrollment tracking against either a single
tutorial or a full learning path (exactly one, never both — enrolling
in a path is a distinct unit of progress from enrolling in one of its
tutorials directly). Status is a simple field guarded directly here:
enrolled -> in_progress -> completed/abandoned. `update_progress`
auto-advances enrolled -> in_progress on the first progress update,
and auto-completes once progress crosses the pass threshold (the
enrolled tutorial's own `pass_threshold_pct`, or 100% for a learning
path, since a path's "pass threshold" is just finishing every step)."""
from __future__ import annotations


from docs_platform.core.exceptions import EnrollmentNotFoundError, InvalidTransitionError, ValidationError
from docs_platform.domain.enums import EnrollmentStatus
from docs_platform.models.learning import EnrollmentModel
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.clock import utc_now

_ENROLLMENT_TRANSITIONS: dict[EnrollmentStatus, set[EnrollmentStatus]] = {
    EnrollmentStatus.ENROLLED: {EnrollmentStatus.IN_PROGRESS, EnrollmentStatus.ABANDONED},
    EnrollmentStatus.IN_PROGRESS: {EnrollmentStatus.COMPLETED, EnrollmentStatus.ABANDONED},
    EnrollmentStatus.COMPLETED: set(),
    EnrollmentStatus.ABANDONED: set(),
}


class EnrollmentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_or_404(self, tenant_id: str, enrollment_id: str) -> EnrollmentModel:
        enrollment = await self.repos.enrollments.get_or_404(enrollment_id)
        if enrollment.tenant_id != tenant_id:
            raise EnrollmentNotFoundError(f"Enrollment '{enrollment_id}' not found for tenant '{tenant_id}'")
        return enrollment

    async def enroll(
        self, tenant_id: str, user_id: str, *, tutorial_id: str | None = None, learning_path_id: str | None = None
    ) -> EnrollmentModel:
        if bool(tutorial_id) == bool(learning_path_id):
            raise ValidationError("Enroll with exactly one of tutorial_id or learning_path_id")

        existing = (
            await self.repos.enrollments.get_for_user_and_tutorial(tenant_id, user_id, tutorial_id)
            if tutorial_id
            else await self.repos.enrollments.get_for_user_and_path(tenant_id, user_id, learning_path_id)
        )
        if existing is not None:
            return existing

        enrollment = EnrollmentModel(
            tenant_id=tenant_id, user_id=user_id, tutorial_id=tutorial_id, learning_path_id=learning_path_id,
            status=EnrollmentStatus.ENROLLED.value, progress_pct=0.0,
        )
        return await self.repos.enrollments.add(enrollment)

    async def _transition(self, tenant_id: str, enrollment_id: str, target: EnrollmentStatus) -> EnrollmentModel:
        enrollment = await self.get_or_404(tenant_id, enrollment_id)
        current = EnrollmentStatus(enrollment.status)
        if target not in _ENROLLMENT_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(f"Enrollment '{enrollment_id}' cannot transition from {current.value} to {target.value}")
        enrollment.status = target.value
        return enrollment

    async def update_progress(self, tenant_id: str, enrollment_id: str, *, progress_pct: float, pass_threshold_pct: float = 100.0) -> EnrollmentModel:
        enrollment = await self.get_or_404(tenant_id, enrollment_id)
        if enrollment.status == EnrollmentStatus.ENROLLED.value:
            enrollment = await self._transition(tenant_id, enrollment_id, EnrollmentStatus.IN_PROGRESS)
        elif enrollment.status not in (EnrollmentStatus.IN_PROGRESS.value,):
            raise InvalidTransitionError(f"Enrollment '{enrollment_id}' is '{enrollment.status}' and can no longer be updated")

        enrollment.progress_pct = progress_pct
        if progress_pct >= pass_threshold_pct:
            enrollment.status = EnrollmentStatus.COMPLETED.value
            enrollment.completed_at = utc_now()
        return await self.repos.enrollments.update(enrollment)

    async def abandon(self, tenant_id: str, enrollment_id: str) -> EnrollmentModel:
        enrollment = await self._transition(tenant_id, enrollment_id, EnrollmentStatus.ABANDONED)
        return await self.repos.enrollments.update(enrollment)

    async def list_for_user(self, tenant_id: str, user_id: str) -> list[EnrollmentModel]:
        return await self.repos.enrollments.list_for_user(tenant_id, user_id)
