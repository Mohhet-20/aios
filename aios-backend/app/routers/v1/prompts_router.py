from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_prompt_service
from app.schemas.prompt import (
    PromptCreate,
    PromptPromoteRequest,
    PromptRead,
    PromptRenderRequest,
    PromptVersionCreate,
    PromptVersionRead,
)
from app.security.permissions import Permission
from app.security.principal import Principal
from app.services.prompt_service import PromptService

router = APIRouter(prefix="/prompts", tags=["Prompts"])


@router.post("", response_model=PromptRead, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptCreate,
    service: PromptService = Depends(get_prompt_service),
    _principal=Depends(require_permission(Permission.PROMPT_WRITE)),
):
    from app.models.prompt import PromptModel

    prompt = PromptModel(
        workspace_id=payload.workspace_id,
        name=payload.name,
        description=payload.description,
        target_model=payload.target_model,
        tags=",".join(payload.tags),
    )
    return await service.prompts.add(prompt)


@router.get("", response_model=list[PromptRead])
async def list_prompts(
    workspace_id: str | None = Query(default=None), service: PromptService = Depends(get_prompt_service)
):
    return (
        await service.prompts.list(workspace_id=workspace_id)
        if workspace_id
        else await service.prompts.list()
    )


@router.get("/{prompt_id}", response_model=PromptRead)
async def get_prompt(prompt_id: str, service: PromptService = Depends(get_prompt_service)):
    return await service.prompts.get_or_404(prompt_id)


@router.get("/{prompt_id}/versions", response_model=list[PromptVersionRead])
async def list_versions(prompt_id: str, service: PromptService = Depends(get_prompt_service)):
    return await service.versions.list_for_prompt(prompt_id)


@router.post("/{prompt_id}/versions", response_model=PromptVersionRead, status_code=status.HTTP_201_CREATED)
async def create_version(
    prompt_id: str,
    payload: PromptVersionCreate,
    service: PromptService = Depends(get_prompt_service),
    principal: Principal = Depends(require_permission(Permission.PROMPT_WRITE)),
):
    return await service.create_version(prompt_id, payload.content, principal.id)


@router.post("/{prompt_id}/versions/{version}/promote", response_model=PromptVersionRead)
async def promote_version(
    prompt_id: str,
    version: int,
    payload: PromptPromoteRequest,
    service: PromptService = Depends(get_prompt_service),
    principal: Principal = Depends(require_permission(Permission.PROMPT_PROMOTE)),
):
    return await service.promote_version(prompt_id, version, payload.target_status, principal.id)


@router.post("/{prompt_id}/render")
async def render_prompt(
    prompt_id: str, payload: PromptRenderRequest, service: PromptService = Depends(get_prompt_service)
):
    rendered = await service.render(prompt_id, payload.variables)
    return {"prompt_id": prompt_id, "rendered": rendered}
