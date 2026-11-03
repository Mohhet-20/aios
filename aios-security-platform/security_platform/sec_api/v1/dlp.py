"""DLP API: policy evaluation (allow/flag/redact/block) and secure
context assembly for LLM-bound content."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from security_platform.dependencies.dependencies import get_current_tenant_id, get_dlp_service
from security_platform.dlp.dlp_service import DlpService
from security_platform.sec_api.serialization import to_dict_list

router = APIRouter(prefix="/dlp", tags=["dlp"])


class EvaluateRequest(BaseModel):
    text: str
    resource_type: str | None = None
    resource_id: str | None = None


@router.post("/evaluate", status_code=201)
async def evaluate(body: EvaluateRequest, tenant_id: str = Depends(get_current_tenant_id), service: DlpService = Depends(get_dlp_service)):
    incidents, action, output_text = await service.evaluate_dlp(tenant_id, body.text, resource_type=body.resource_type, resource_id=body.resource_id)
    return {"incidents": to_dict_list(incidents), "action": action, "output_text": output_text}


class ContextFragment(BaseModel):
    text: str
    resource_type: str | None = None
    resource_id: str | None = None


class AssembleContextRequest(BaseModel):
    fragments: list[ContextFragment]
    max_sensitivity: str = "confidential"


@router.post("/secure-context")
async def assemble_secure_context(body: AssembleContextRequest, tenant_id: str = Depends(get_current_tenant_id), service: DlpService = Depends(get_dlp_service)):
    fragments = [f.model_dump() for f in body.fragments]
    return {"fragments": await service.assemble_secure_context(tenant_id, fragments, max_sensitivity=body.max_sensitivity)}
