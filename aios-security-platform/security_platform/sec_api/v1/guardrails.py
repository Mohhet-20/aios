"""AI Guardrails API: prompt evaluation (injection/jailbreak/unsafe-
instruction detection, with block enforcement raising through the
exception-handler layer as HTTP 451), structured output validation,
response filtering, and the violation review lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from security_platform.dependencies.dependencies import get_current_actor_id, get_current_tenant_id, get_guardrail_service, get_guardrail_violation_service
from security_platform.guardrails.guardrail_service import GuardrailService
from security_platform.guardrails.violation_service import GuardrailViolationService
from security_platform.sec_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


class EvaluatePromptRequest(BaseModel):
    text: str
    source: str = "user"
    resource_type: str | None = None
    resource_id: str | None = None


@router.post("/evaluate-prompt", status_code=201)
async def evaluate_prompt(
    body: EvaluatePromptRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: GuardrailService = Depends(get_guardrail_service),
):
    return to_dict(
        await service.evaluate_prompt(
            tenant_id, body.text, source=body.source, actor_id=actor_id, resource_type=body.resource_type, resource_id=body.resource_id
        )
    )


class ValidateOutputRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    data: dict | list | str | int | float | bool | None
    schema_: dict = Field(alias="schema")
    resource_type: str | None = None
    resource_id: str | None = None


@router.post("/validate-output", status_code=201)
async def validate_output(
    body: ValidateOutputRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: GuardrailService = Depends(get_guardrail_service),
):
    evaluation, is_valid, errors = await service.validate_output(
        tenant_id, body.data, body.schema_, actor_id=actor_id, resource_type=body.resource_type, resource_id=body.resource_id
    )
    return {"evaluation": to_dict(evaluation), "is_valid": is_valid, "errors": errors}


class FilterResponseRequest(BaseModel):
    text: str
    banned_patterns: list[str]
    resource_type: str | None = None
    resource_id: str | None = None


@router.post("/filter-response", status_code=201)
async def filter_response(
    body: FilterResponseRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: GuardrailService = Depends(get_guardrail_service),
):
    evaluation, filtered_text = await service.filter_response(
        tenant_id, body.text, body.banned_patterns, actor_id=actor_id, resource_type=body.resource_type, resource_id=body.resource_id
    )
    return {"evaluation": to_dict(evaluation), "filtered_text": filtered_text}


@router.get("/violations/open")
async def list_open_violations(tenant_id: str = Depends(get_current_tenant_id), service: GuardrailViolationService = Depends(get_guardrail_violation_service)):
    return to_dict_list(await service.list_open(tenant_id))


@router.post("/violations/{violation_id}/acknowledge")
async def acknowledge_violation(
    violation_id: str, tenant_id: str = Depends(get_current_tenant_id), service: GuardrailViolationService = Depends(get_guardrail_violation_service)
):
    return to_dict(await service.acknowledge(tenant_id, violation_id))


class ResolveViolationRequest(BaseModel):
    resolution_notes: str | None = None


@router.post("/violations/{violation_id}/resolve")
async def resolve_violation(
    violation_id: str, body: ResolveViolationRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: GuardrailViolationService = Depends(get_guardrail_violation_service),
):
    return to_dict(await service.resolve(tenant_id, violation_id, resolution_notes=body.resolution_notes))
