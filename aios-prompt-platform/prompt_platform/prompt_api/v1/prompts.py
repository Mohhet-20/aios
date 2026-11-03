"""Prompt CRUD, dependency graph, and the Prompt Library surface (search,
favorites, tags, categories, collections, recently/most used)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.core.pagination import PaginationParams
from prompt_platform.domain.enums import DependencyRelationship
from prompt_platform.prompt_api.dependencies import (
    get_current_actor_id,
    get_library_service,
    get_prompt_service,
    get_repos,
)
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_engine.prompt_service import PromptService
from prompt_platform.prompt_registry.library_service import PromptLibraryService
from prompt_platform.repositories.registry import RepositoryRegistry

router = APIRouter(prefix="/prompts", tags=["prompts"])


class CreatePromptRequest(BaseModel):
    workspace_id: str
    project_id: str
    name: str
    description: str | None = None
    slug: str | None = None


class UpdatePromptRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None
    category_id: str | None = None


class AddDependencyRequest(BaseModel):
    depends_on_prompt_id: str
    relationship_type: DependencyRelationship = DependencyRelationship.REFERENCE


class TagRequest(BaseModel):
    tag_name: str


@router.post("", status_code=201)
async def create_prompt(body: CreatePromptRequest, actor_id: str = Depends(get_current_actor_id), svc: PromptService = Depends(get_prompt_service)):
    prompt = await svc.create_prompt(workspace_id=body.workspace_id, project_id=body.project_id, name=body.name, owner_id=actor_id, description=body.description, slug=body.slug)
    return to_dict(prompt)


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.prompts.get_or_404(prompt_id))


@router.patch("/{prompt_id}")
async def update_prompt(prompt_id: str, body: UpdatePromptRequest, actor_id: str = Depends(get_current_actor_id), svc: PromptService = Depends(get_prompt_service)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    return to_dict(await svc.update_metadata(prompt_id, actor_id, **fields))


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(prompt_id: str, actor_id: str = Depends(get_current_actor_id), svc: PromptService = Depends(get_prompt_service)):
    await svc.delete_prompt(prompt_id, actor_id)


@router.post("/{prompt_id}/dependencies", status_code=201)
async def add_dependency(prompt_id: str, body: AddDependencyRequest, svc: PromptService = Depends(get_prompt_service)):
    return to_dict(await svc.add_dependency(prompt_id, body.depends_on_prompt_id, body.relationship_type))


@router.get("/{prompt_id}/dependencies")
async def list_dependencies(prompt_id: str, svc: PromptService = Depends(get_prompt_service)):
    return to_dict_list(await svc.list_dependencies(prompt_id))


# -- library: search / favorites / tags / categories / collections -------------------

@router.get("")
async def search_prompts(
    workspace_id: str, query: str | None = None, category_id: str | None = None, visibility: str | None = None,
    status: str | None = None, owner_id: str | None = None, sort: str = "updated_at", page: int = 1, page_size: int = 20,
    svc: PromptLibraryService = Depends(get_library_service),
):
    result = await svc.search(
        workspace_id, query=query, category_id=category_id, visibility=visibility, status=status, owner_id=owner_id,
        sort=sort, pagination=PaginationParams(page=page, page_size=page_size),
    )
    return {"items": to_dict_list(result.items), "total": result.total, "page": result.page, "page_size": result.page_size}


@router.post("/{prompt_id}/favorite", status_code=204)
async def favorite_prompt(prompt_id: str, actor_id: str = Depends(get_current_actor_id), svc: PromptLibraryService = Depends(get_library_service)):
    await svc.add_favorite(actor_id, prompt_id)


@router.delete("/{prompt_id}/favorite", status_code=204)
async def unfavorite_prompt(prompt_id: str, actor_id: str = Depends(get_current_actor_id), svc: PromptLibraryService = Depends(get_library_service)):
    await svc.remove_favorite(actor_id, prompt_id)


@router.get("/library/favorites")
async def list_favorites(actor_id: str = Depends(get_current_actor_id), svc: PromptLibraryService = Depends(get_library_service)):
    return to_dict_list(await svc.list_favorites(actor_id))


@router.get("/library/recently-used")
async def recently_used(workspace_id: str, limit: int = 10, svc: PromptLibraryService = Depends(get_library_service)):
    return to_dict_list(await svc.list_recently_used(workspace_id, limit=limit))


@router.get("/library/most-used")
async def most_used(workspace_id: str, limit: int = 10, svc: PromptLibraryService = Depends(get_library_service)):
    results = await svc.list_most_used(workspace_id, limit=limit)
    return [{"prompt": to_dict(p), "execution_count": count} for p, count in results]


@router.post("/{prompt_id}/archive")
async def archive_prompt(prompt_id: str, svc: PromptLibraryService = Depends(get_library_service)):
    return to_dict(await svc.archive(prompt_id))


@router.post("/{prompt_id}/unarchive")
async def unarchive_prompt(prompt_id: str, svc: PromptLibraryService = Depends(get_library_service)):
    return to_dict(await svc.unarchive(prompt_id))


@router.post("/{prompt_id}/tags", status_code=204)
async def tag_prompt(prompt_id: str, body: TagRequest, svc: PromptLibraryService = Depends(get_library_service)):
    await svc.tag_prompt(prompt_id, body.tag_name)


@router.delete("/{prompt_id}/tags/{tag_name}", status_code=204)
async def untag_prompt(prompt_id: str, tag_name: str, svc: PromptLibraryService = Depends(get_library_service)):
    await svc.untag_prompt(prompt_id, tag_name)


@router.get("/library/categories")
async def list_categories(svc: PromptLibraryService = Depends(get_library_service)):
    return to_dict_list(await svc.list_categories())


class CreateCategoryRequest(BaseModel):
    name: str
    slug: str
    description: str | None = None


@router.post("/library/categories", status_code=201)
async def create_category(body: CreateCategoryRequest, svc: PromptLibraryService = Depends(get_library_service)):
    return to_dict(await svc.create_category(body.name, body.slug, body.description))


class CreateCollectionRequest(BaseModel):
    workspace_id: str
    name: str
    description: str | None = None
    is_shared: bool = False


@router.post("/library/collections", status_code=201)
async def create_collection(body: CreateCollectionRequest, actor_id: str = Depends(get_current_actor_id), svc: PromptLibraryService = Depends(get_library_service)):
    return to_dict(await svc.create_collection(body.workspace_id, body.name, actor_id, description=body.description, is_shared=body.is_shared))


@router.get("/library/collections")
async def list_collections(workspace_id: str, svc: PromptLibraryService = Depends(get_library_service)):
    return to_dict_list(await svc.list_collections(workspace_id))


@router.post("/library/collections/{collection_id}/prompts/{prompt_id}", status_code=204)
async def add_to_collection(collection_id: str, prompt_id: str, svc: PromptLibraryService = Depends(get_library_service)):
    await svc.add_to_collection(collection_id, prompt_id)


@router.delete("/library/collections/{collection_id}/prompts/{prompt_id}", status_code=204)
async def remove_from_collection(collection_id: str, prompt_id: str, svc: PromptLibraryService = Depends(get_library_service)):
    await svc.remove_from_collection(collection_id, prompt_id)


@router.get("/library/collections/{collection_id}/prompts")
async def list_collection_prompts(collection_id: str, svc: PromptLibraryService = Depends(get_library_service)):
    return to_dict_list(await svc.list_collection_prompts(collection_id))
