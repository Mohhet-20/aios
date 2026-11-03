from fastapi import APIRouter, Depends, status

from app.dependencies.auth_dependencies import get_current_principal
from app.dependencies.service_dependencies import get_auth_service
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserRead
from app.security.jwt import TokenType, decode_token
from app.security.permissions import Role
from app.security.principal import Principal
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    user = await auth_service.register(payload.email, payload.password, payload.full_name)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    user = await auth_service.authenticate(payload.email, payload.password)
    tokens = await auth_service.issue_tokens(user, payload.organization_id, Role.MEMBER)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)):
    tokens = await auth_service.refresh(payload.refresh_token, organization_id=None)
    return TokenResponse(**tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)):
    token_payload = decode_token(payload.refresh_token, TokenType.REFRESH)
    await auth_service.revoke_refresh_token(token_payload.jti)


@router.get("/me")
async def me(principal: Principal = Depends(get_current_principal)):
    return {
        "id": principal.id,
        "organization_id": principal.organization_id,
        "role": principal.role.value,
        "permissions": sorted(p.value for p in principal.permissions),
        "is_service_account": principal.is_service_account,
    }
