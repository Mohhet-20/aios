"""Prompt Studio: validate/format a draft, live preview (token estimate,
context window, JSON preview), execute a draft against a real model
without persisting, and autosave. Operates on unsaved draft text except
for autosave, which patches a DRAFT-status persisted version."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.config.settings import get_settings
from prompt_platform.prompt_api.dependencies import (
    get_autosave_service,
    get_preview_service,
    get_studio_execution_service,
)
from prompt_platform.prompt_api.serialization import to_dict
from prompt_platform.prompt_editor.autosave import AutosaveService
from prompt_platform.prompt_editor.execution import StudioExecutionService
from prompt_platform.prompt_editor.formatting import format_template
from prompt_platform.prompt_editor.preview import PreviewService
from prompt_platform.prompt_editor.validation import validate_draft

router = APIRouter(prefix="/studio", tags=["studio"])


class DraftRequest(BaseModel):
    system_template: str | None = None
    developer_template: str | None = None
    user_template: str
    variables_schema: list[dict] = []
    parameters: dict = {}


class RenderRequest(DraftRequest):
    variables: dict = {}


class AutosaveRequest(BaseModel):
    expected_version: int
    system_template: str | None = None
    developer_template: str | None = None
    user_template: str | None = None
    variables_schema: list[dict] | None = None
    parameters: dict | None = None


@router.post("/validate")
async def validate(body: DraftRequest):
    settings = get_settings()
    report = validate_draft(
        system_template=body.system_template, developer_template=body.developer_template, user_template=body.user_template,
        variables_schema=body.variables_schema, parameters=body.parameters, max_chars=settings.max_prompt_template_chars,
    )
    return {"is_valid": report.is_valid, "issues": [asdict(i) for i in report.issues]}


@router.post("/format")
async def format_draft(body: DraftRequest):
    return {
        "system_template": format_template(body.system_template),
        "developer_template": format_template(body.developer_template),
        "user_template": format_template(body.user_template),
    }


@router.post("/preview")
async def preview(body: RenderRequest, svc: PreviewService = Depends(get_preview_service)):
    result = svc.render(
        system_template=body.system_template, developer_template=body.developer_template, user_template=body.user_template,
        variables=body.variables, parameters=body.parameters,
    )
    return {
        "rendered_messages": result.rendered_messages, "token_estimate": result.token_estimate,
        "context_window": asdict(result.context_window) if result.context_window else None, "json_preview": result.json_preview,
    }


@router.post("/run")
async def run(body: RenderRequest, svc: StudioExecutionService = Depends(get_studio_execution_service)):
    response = await svc.run(
        system_template=body.system_template, developer_template=body.developer_template, user_template=body.user_template,
        variables=body.variables, parameters=body.parameters,
    )
    return response.model_dump(mode="json")


@router.post("/run-structured")
async def run_structured(body: RenderRequest, json_schema: dict, svc: StudioExecutionService = Depends(get_studio_execution_service)):
    result = await svc.run_structured(
        system_template=body.system_template, developer_template=body.developer_template, user_template=body.user_template,
        variables=body.variables, parameters=body.parameters, json_schema=json_schema,
    )
    return result


@router.patch("/versions/{version_id}/autosave")
async def autosave(version_id: str, body: AutosaveRequest, svc: AutosaveService = Depends(get_autosave_service)):
    version = await svc.save_draft(
        version_id, expected_version=body.expected_version, system_template=body.system_template,
        developer_template=body.developer_template, user_template=body.user_template,
        variables_schema=body.variables_schema, parameters=body.parameters,
    )
    return to_dict(version)
