from fastapi import APIRouter, Depends

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_user_service
from app.schemas.auth import UserRead
from app.security.permissions import Permission
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserRead])
async def list_users(
    service: UserService = Depends(get_user_service),
    _principal=Depends(require_permission(Permission.USER_MANAGE)),
):
    return await service.list()


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: str, service: UserService = Depends(get_user_service)):
    return await service.get(user_id)
