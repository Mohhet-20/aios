"""Import/export: serialize a prompt (metadata + full version history) to
a portable JSON bundle, and recreate one from such a bundle — e.g. moving
a prompt between workspaces or environments, or checking a prompt into
external version control.

Export is scoped under a specific prompt (`/prompts/{prompt_id}/export`);
import creates a brand-new prompt, so it lives at the unscoped
`/prompts/import` instead of nesting under a `{prompt_id}` it doesn't
have yet.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.prompt_api.dependencies import get_current_actor_id, get_repos
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_engine.prompt_service import PromptService
from prompt_platform.prompt_engine.versioning_service import VersioningService
from prompt_platform.repositories.registry import RepositoryRegistry

router = APIRouter(prefix="/prompts", tags=["import-export"])


class ImportVersionIn(BaseModel):
    user_template: str
    system_template: str | None = None
    developer_template: str | None = None
    variables_schema: list[dict] = []
    parameters: dict = {}


class ImportPromptRequest(BaseModel):
    workspace_id: str
    project_id: str
    name: str
    description: str | None = None
    slug: str | None = None
    versions: list[ImportVersionIn] = []


@router.get("/{prompt_id}/export")
async def export_prompt(prompt_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    prompt = await repos.prompts.get_or_404(prompt_id)
    versions = await repos.versions.list_for_prompt(prompt_id)
    return {"prompt": to_dict(prompt), "versions": to_dict_list(versions)}


@router.post("/import", status_code=201)
async def import_prompt(
    body: ImportPromptRequest, actor_id: str = Depends(get_current_actor_id),
    repos: RepositoryRegistry = Depends(get_repos),
):
    prompt_svc = PromptService(repos)
    versioning_svc = VersioningService(repos)

    prompt = await prompt_svc.create_prompt(
        workspace_id=body.workspace_id, project_id=body.project_id, name=body.name,
        owner_id=actor_id, description=body.description, slug=body.slug,
    )
    created_versions = []
    for v in body.versions:
        version = await versioning_svc.create_version(
            prompt.id, user_template=v.user_template, actor_id=actor_id, system_template=v.system_template,
            developer_template=v.developer_template, variables_schema=v.variables_schema, parameters=v.parameters,
        )
        created_versions.append(version)

    return {"prompt": to_dict(prompt), "versions": to_dict_list(created_versions)}
