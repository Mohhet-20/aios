"""PII API: scanning (persisted findings, no raw values stored),
automatic masking, and sensitive data classification."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from security_platform.dependencies.dependencies import get_current_actor_id, get_current_tenant_id, get_pii_service
from security_platform.pii.pii_service import PiiService
from security_platform.sec_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/pii", tags=["pii"])


class ScanRequest(BaseModel):
    source_type: str
    source_id: str | None = None
    text: str


@router.post("/scan", status_code=201)
async def scan(body: ScanRequest, tenant_id: str = Depends(get_current_tenant_id), service: PiiService = Depends(get_pii_service)):
    return to_dict_list(await service.scan_pii(tenant_id, body.source_type, body.source_id, body.text))


class MaskRequest(BaseModel):
    text: str


@router.post("/mask")
async def mask(body: MaskRequest, service: PiiService = Depends(get_pii_service)):
    return {"masked_text": service.mask_text(body.text)}


class ClassifyRequest(BaseModel):
    resource_type: str
    resource_id: str
    sensitivity: str
    rationale: str | None = None


@router.post("/classify", status_code=201)
async def classify(
    body: ClassifyRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: PiiService = Depends(get_pii_service),
):
    return to_dict(
        await service.classify_resource(
            tenant_id, body.resource_type, body.resource_id, body.sensitivity, classified_by=actor_id, rationale=body.rationale
        )
    )
