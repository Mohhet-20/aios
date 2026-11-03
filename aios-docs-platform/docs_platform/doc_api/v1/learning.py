"""Learning Platform: tutorials (getting-started, interactive,
hands-on lab, step-by-step), role-based learning paths, and the
enrollment/progress lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_enrollment_service,
    get_learning_path_service,
    get_tutorial_service,
)
from docs_platform.doc_api.serialization import to_dict, to_dict_list
from docs_platform.learning.enrollment_service import EnrollmentService
from docs_platform.learning.learning_path_service import LearningPathService
from docs_platform.learning.tutorial_service import TutorialService

router = APIRouter(prefix="/tutorials", tags=["learning"])
paths_router = APIRouter(prefix="/learning-paths", tags=["learning"])
enrollments_router = APIRouter(prefix="/enrollments", tags=["learning"])


class CreateTutorialRequest(BaseModel):
    tutorial_type: str
    title: str
    role: str
    steps: list[dict] | None = None
    pass_threshold_pct: float | None = None


@router.post("", status_code=201)
async def create_tutorial(
    body: CreateTutorialRequest, tenant_id: str = Depends(get_current_tenant_id), service: TutorialService = Depends(get_tutorial_service),
):
    return to_dict(await service.create_tutorial(tenant_id, **body.model_dump()))


@router.get("")
async def list_tutorials(
    role: str | None = None, tutorial_type: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id), service: TutorialService = Depends(get_tutorial_service),
):
    return to_dict_list(await service.list_tutorials(tenant_id, role=role, tutorial_type=tutorial_type))


@router.get("/{tutorial_id}")
async def get_tutorial(
    tutorial_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TutorialService = Depends(get_tutorial_service),
):
    return to_dict(await service.get_or_404(tenant_id, tutorial_id))


class CreatePathRequest(BaseModel):
    name: str
    role: str
    tutorial_ids: list[str] | None = None


@paths_router.post("", status_code=201)
async def create_path(
    body: CreatePathRequest, tenant_id: str = Depends(get_current_tenant_id), service: LearningPathService = Depends(get_learning_path_service),
):
    return to_dict(await service.create_path(tenant_id, **body.model_dump()))


@paths_router.get("")
async def list_paths(
    role: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: LearningPathService = Depends(get_learning_path_service),
):
    return to_dict_list(await service.list_paths(tenant_id, role=role))


@paths_router.get("/{path_id}")
async def get_path(
    path_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LearningPathService = Depends(get_learning_path_service),
):
    return to_dict(await service.get_or_404(tenant_id, path_id))


class EnrollRequest(BaseModel):
    user_id: str
    tutorial_id: str | None = None
    learning_path_id: str | None = None


@enrollments_router.post("", status_code=201)
async def enroll(
    body: EnrollRequest, tenant_id: str = Depends(get_current_tenant_id), service: EnrollmentService = Depends(get_enrollment_service),
):
    payload = body.model_dump()
    user_id = payload.pop("user_id")
    return to_dict(await service.enroll(tenant_id, user_id, **payload))


@enrollments_router.get("/{enrollment_id}")
async def get_enrollment(
    enrollment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EnrollmentService = Depends(get_enrollment_service),
):
    return to_dict(await service.get_or_404(tenant_id, enrollment_id))


class UpdateProgressRequest(BaseModel):
    progress_pct: float
    pass_threshold_pct: float = 100.0


@enrollments_router.put("/{enrollment_id}/progress")
async def update_progress(
    enrollment_id: str, body: UpdateProgressRequest,
    tenant_id: str = Depends(get_current_tenant_id), service: EnrollmentService = Depends(get_enrollment_service),
):
    return to_dict(await service.update_progress(tenant_id, enrollment_id, **body.model_dump()))


@enrollments_router.post("/{enrollment_id}/abandon")
async def abandon_enrollment(
    enrollment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EnrollmentService = Depends(get_enrollment_service),
):
    return to_dict(await service.abandon(tenant_id, enrollment_id))


@enrollments_router.get("/by-user/{user_id}")
async def list_enrollments_for_user(
    user_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EnrollmentService = Depends(get_enrollment_service),
):
    return to_dict_list(await service.list_for_user(tenant_id, user_id))
