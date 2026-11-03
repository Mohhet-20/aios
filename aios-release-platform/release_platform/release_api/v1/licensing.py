"""License Manager: enterprise/organization/trial/feature/seat-based
licenses, seat assignment, and status lifecycle."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import get_current_tenant_id, get_license_service
from release_platform.licensing.license_service import LicenseService
from release_platform.release_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/licenses", tags=["licensing"])


class IssueLicenseRequest(BaseModel):
    org_ref: str
    license_type: str
    seats_total: int = 0
    features: list[str] | None = None
    expires_at: datetime | None = None


@router.post("", status_code=201)
async def issue_license(
    body: IssueLicenseRequest, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    return to_dict(await service.issue_license(tenant_id, **body.model_dump()))


@router.get("/by-org/{org_ref}")
async def list_for_org(
    org_ref: str, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    return to_dict_list(await service.list_for_org(tenant_id, org_ref))


@router.get("/{license_id}")
async def get_license(
    license_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    return to_dict(await service.get_or_404(tenant_id, license_id))


@router.post("/{license_id}/assign-seat")
async def assign_seat(
    license_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    return to_dict(await service.assign_seat(tenant_id, license_id))


@router.post("/{license_id}/release-seat")
async def release_seat(
    license_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    return to_dict(await service.release_seat(tenant_id, license_id))


@router.post("/{license_id}/activate")
async def activate_license(
    license_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    return to_dict(await service.activate(tenant_id, license_id))


@router.post("/{license_id}/suspend")
async def suspend_license(
    license_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    return to_dict(await service.suspend(tenant_id, license_id))


@router.post("/{license_id}/revoke")
async def revoke_license(
    license_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    return to_dict(await service.revoke(tenant_id, license_id))


@router.get("/{license_id}/assert-active")
async def assert_active(
    license_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    lic = await service.assert_active(tenant_id, license_id)
    return {"license_id": lic.id, "active": True}


@router.get("/{license_id}/has-feature/{feature}")
async def has_feature(
    license_id: str, feature: str, tenant_id: str = Depends(get_current_tenant_id), service: LicenseService = Depends(get_license_service),
):
    return {"license_id": license_id, "feature": feature, "has_feature": await service.has_feature(tenant_id, license_id, feature)}
