"""Registration, email verification, password login/change/reset, and
magic-link sign-in."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.authentication.email_verification_service import EmailVerificationService
from identity_platform.authentication.login_service import LoginService
from identity_platform.authentication.magic_link_service import MagicLinkService
from identity_platform.authentication.password_service import PasswordService
from identity_platform.authentication.registration_service import RegistrationService
from identity_platform.config.settings import Settings
from identity_platform.core.exceptions import AuthorizationError, InvalidMfaCodeError, MfaRequiredError, NotFoundError
from identity_platform.dependencies.dependencies import (
    get_email_verification_service,
    get_login_service,
    get_magic_link_service,
    get_mfa_service,
    get_password_service,
    get_registration_service,
    get_repos,
    get_session_service,
    get_settings_dep,
)
from identity_platform.identity_api.serialization import to_dict
from identity_platform.domain.enums import MembershipStatus, UserStatus
from identity_platform.mfa.mfa_service import MfaService
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.sessions.session_service import SessionService

router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, service: RegistrationService = Depends(get_registration_service)):
    result = await service.register(email=body.email, raw_password=body.password, display_name=body.display_name)
    return {"user": to_dict(result.user), "verification_token": result.raw_verification_token}


class VerifyEmailRequest(BaseModel):
    token: str


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, service: EmailVerificationService = Depends(get_email_verification_service)):
    return to_dict(await service.verify(body.token))


class ResendVerificationRequest(BaseModel):
    user_id: str


@router.post("/resend-verification")
async def resend_verification(body: ResendVerificationRequest, service: EmailVerificationService = Depends(get_email_verification_service)):
    return {"verification_token": await service.request_verification(body.user_id)}


class LoginRequest(BaseModel):
    email: str
    password: str
    ip_address: str | None = None
    user_agent: str | None = None


@router.post("/login")
async def login(body: LoginRequest, service: LoginService = Depends(get_login_service)):
    user = await service.authenticate(email=body.email, raw_password=body.password, ip_address=body.ip_address, user_agent=body.user_agent)
    return to_dict(user)


class TokenRequest(BaseModel):
    email: str
    password: str
    mfa_code: str | None = None
    organization_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


@router.post("/token")
async def issue_token(
    body: TokenRequest,
    login: LoginService = Depends(get_login_service),
    mfa: MfaService = Depends(get_mfa_service),
    sessions: SessionService = Depends(get_session_service),
):
    """Password sign-in that ends in a session: verifies the password (lockout and verification rules apply), then
    the TOTP or recovery code when the account has MFA, and only then issues the access and refresh tokens. This is
    the endpoint the console's edge calls; raw ``POST /sessions`` is for already-authenticated internal flows."""
    user = await login.authenticate(email=body.email, raw_password=body.password, ip_address=body.ip_address, user_agent=body.user_agent)
    if await mfa.has_active_factor(user.id):
        if not body.mfa_code:
            raise MfaRequiredError("this account requires a multi-factor code")
        if not await mfa.verify_login_code(user.id, body.mfa_code):
            raise InvalidMfaCodeError("the multi-factor code is not valid")
    result = await sessions.create_session(
        user.id, organization_id=body.organization_id or user.primary_organization_id,
        ip_address=body.ip_address, user_agent=body.user_agent,
    )
    return {
        "user": to_dict(user), "session": to_dict(result.session),
        "access_token": result.access_token, "refresh_token": result.raw_refresh_token,
    }


# Roles whose holders are never signed in through the public guest endpoint.
PRIVILEGED_ROLE_SLUGS = frozenset({"system_admin", "org_owner", "org_admin", "workspace_admin"})


class GuestRequest(BaseModel):
    ip_address: str | None = None
    user_agent: str | None = None


@router.post("/guest")
async def guest_session(
    body: GuestRequest,
    repos: RepositoryRegistry = Depends(get_repos),
    sessions: SessionService = Depends(get_session_service),
    settings: Settings = Depends(get_settings_dep),
):
    """Public demo sign-in: a session for the configured guest account, with no password involved. 404 unless
    GUEST_ACCESS_ENABLED and GUEST_EMAIL are set. Refused (403) if that account owns an organisation or holds an
    administrative role anywhere, so a misconfiguration can never hand visitors an administrator. Like every route
    here it is reachable only through the console's edge (X-Internal-Token)."""
    email = settings.guest_email.strip().lower()
    if not settings.guest_access_enabled or not email:
        raise NotFoundError("guest access is not enabled on this deployment")
    user = await repos.users.get_by_email(email)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise NotFoundError("the guest account is not set up on this deployment")
    # A member (not an owner) has no primary organisation; use the organisation they actively belong to.
    org_id = user.primary_organization_id
    if org_id is None:
        active = [m for m in await repos.organization_memberships.list_for_user(user.id) if m.status == MembershipStatus.ACTIVE.value]
        org_id = active[0].organization_id if active else None
    if org_id is None:
        raise NotFoundError("the guest account is not a member of any organisation")
    org = await repos.organizations.get(org_id)
    if org is not None and org.owner_user_id == user.id:
        raise AuthorizationError("guest access is misconfigured: the guest account owns its organisation")
    for assignment in await repos.role_assignments.list_for_principal("user", user.id):
        role = await repos.roles.get(assignment.role_id)
        if role is not None and role.slug in PRIVILEGED_ROLE_SLUGS:
            raise AuthorizationError("guest access is misconfigured: the guest account holds an administrative role")
    result = await sessions.create_session(
        user.id, organization_id=org_id, ip_address=body.ip_address, user_agent=body.user_agent,
    )
    return {
        "user": to_dict(user), "session": to_dict(result.session),
        "access_token": result.access_token, "refresh_token": result.raw_refresh_token,
    }


class ChangePasswordRequest(BaseModel):
    user_id: str
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, service: PasswordService = Depends(get_password_service)):
    await service.change_password(body.user_id, current_password=body.current_password, new_password=body.new_password)
    return {"status": "ok"}


class RequestPasswordResetRequest(BaseModel):
    email: str
    ip_address: str | None = None


@router.post("/request-password-reset")
async def request_password_reset(body: RequestPasswordResetRequest, service: PasswordService = Depends(get_password_service)):
    token = await service.request_reset(body.email, ip_address=body.ip_address)
    return {"reset_token": token}


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, service: PasswordService = Depends(get_password_service)):
    return to_dict(await service.reset_with_token(body.token, body.new_password))


class MagicLinkRequestRequest(BaseModel):
    email: str


@router.post("/magic-link/request")
async def request_magic_link(body: MagicLinkRequestRequest, service: MagicLinkService = Depends(get_magic_link_service)):
    return {"magic_link_token": await service.request_link(body.email)}


class MagicLinkRedeemRequest(BaseModel):
    token: str


@router.post("/magic-link/redeem")
async def redeem_magic_link(body: MagicLinkRedeemRequest, service: MagicLinkService = Depends(get_magic_link_service)):
    return to_dict(await service.redeem(body.token))
