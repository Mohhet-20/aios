"""Hallucination Detection: run a grounding check on a claim against
its source context and query prior checks for a subject."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.dependencies.dependencies import get_hallucination_service
from eval_platform.eval_api.serialization import to_dict, to_dict_list
from eval_platform.hallucination.service import HallucinationDetectionService

router = APIRouter(prefix="/hallucination-checks", tags=["hallucination detection"])


class RunCheckRequest(BaseModel):
    workspace_id: str
    claim_text: str
    source_context: list[str]
    subject_type: str
    subject_id: str | None = None
    repeated_claims: list[str] | None = None


@router.post("", status_code=201)
async def run_check(body: RunCheckRequest, service: HallucinationDetectionService = Depends(get_hallucination_service)):
    result = await service.run_check(
        body.workspace_id, claim_text=body.claim_text, source_context=body.source_context, subject_type=body.subject_type,
        subject_id=body.subject_id, repeated_claims=body.repeated_claims,
    )
    return to_dict(result)


@router.get("")
async def list_for_subject(subject_type: str, subject_id: str, service: HallucinationDetectionService = Depends(get_hallucination_service)):
    return to_dict_list(await service.list_for_subject(subject_type, subject_id))
