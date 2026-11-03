"""TOTP MFA enrollment/verification, recovery codes, and trusted-device
management."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_device_trust_service, get_mfa_service
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.mfa.device_trust_service import DeviceTrustService
from identity_platform.mfa.mfa_service import MfaService

router = APIRouter(prefix="/mfa", tags=["mfa"])


class EnrollTotpRequest(BaseModel):
    user_id: str
    account_email: str


@router.post("/totp/enroll")
async def enroll_totp(body: EnrollTotpRequest, service: MfaService = Depends(get_mfa_service)):
    result = await service.enroll_totp(body.user_id, account_email=body.account_email)
    return {"factor_id": result.factor_id, "raw_secret": result.raw_secret, "provisioning_uri": result.provisioning_uri}


class ConfirmEnrollmentRequest(BaseModel):
    factor_id: str
    code: str


@router.post("/totp/confirm")
async def confirm_totp_enrollment(body: ConfirmEnrollmentRequest, service: MfaService = Depends(get_mfa_service)):
    return {"recovery_codes": await service.confirm_enrollment(body.factor_id, body.code)}


class VerifyLoginCodeRequest(BaseModel):
    user_id: str
    code: str


@router.post("/verify")
async def verify_login_code(body: VerifyLoginCodeRequest, service: MfaService = Depends(get_mfa_service)):
    return {"verified": await service.verify_login_code(body.user_id, body.code)}


@router.post("/factors/{factor_id}/disable")
async def disable_factor(factor_id: str, service: MfaService = Depends(get_mfa_service)):
    return to_dict(await service.disable_factor(factor_id))


class RegenerateRecoveryCodesRequest(BaseModel):
    user_id: str


@router.post("/recovery-codes/regenerate")
async def regenerate_recovery_codes(body: RegenerateRecoveryCodesRequest, service: MfaService = Depends(get_mfa_service)):
    return {"recovery_codes": await service.generate_recovery_codes(body.user_id)}


@router.get("/recovery-codes/{user_id}/remaining")
async def remaining_recovery_codes(user_id: str, service: MfaService = Depends(get_mfa_service)):
    return {"remaining": await service.remaining_recovery_code_count(user_id)}


class TrustDeviceRequest(BaseModel):
    user_id: str
    device_fingerprint: str
    device_name: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


@router.post("/devices/trust")
async def trust_device(body: TrustDeviceRequest, service: DeviceTrustService = Depends(get_device_trust_service)):
    token = await service.trust_device(
        body.user_id, device_fingerprint=body.device_fingerprint, device_name=body.device_name,
        ip_address=body.ip_address, user_agent=body.user_agent,
    )
    return {"device_token": token}


@router.get("/devices/{user_id}")
async def list_trusted_devices(user_id: str, service: DeviceTrustService = Depends(get_device_trust_service)):
    return to_dict_list(await service.list_for_user(user_id))


@router.delete("/devices/{device_id}", status_code=204)
async def revoke_trusted_device(device_id: str, service: DeviceTrustService = Depends(get_device_trust_service)):
    await service.revoke(device_id)
