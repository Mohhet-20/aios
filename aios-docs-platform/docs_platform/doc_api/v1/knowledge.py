"""Knowledge Base: articles across 9 types (how-to, best practice,
troubleshooting, FAQ, release note, migration guide, design pattern,
reference, glossary) with a draft -> published -> archived lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.dependencies.dependencies import get_current_tenant_id, get_kb_article_service
from docs_platform.doc_api.serialization import to_dict, to_dict_list
from docs_platform.knowledge.kb_article_service import KbArticleService

router = APIRouter(prefix="/kb-articles", tags=["knowledge-base"])


class CreateArticleRequest(BaseModel):
    article_type: str
    title: str
    slug: str
    content: str = ""
    tags: list[str] | None = None
    owner_id: str | None = None


@router.post("", status_code=201)
async def create_article(
    body: CreateArticleRequest, tenant_id: str = Depends(get_current_tenant_id), service: KbArticleService = Depends(get_kb_article_service),
):
    return to_dict(await service.create_article(tenant_id, **body.model_dump()))


@router.get("")
async def list_articles(
    article_type: str | None = None, status: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id), service: KbArticleService = Depends(get_kb_article_service),
):
    return to_dict_list(await service.list_articles(tenant_id, article_type=article_type, status=status))


@router.get("/by-tag/{tag}")
async def list_articles_by_tag(
    tag: str, tenant_id: str = Depends(get_current_tenant_id), service: KbArticleService = Depends(get_kb_article_service),
):
    return to_dict_list(await service.list_by_tag(tenant_id, tag))


@router.get("/{article_id}")
async def get_article(
    article_id: str, tenant_id: str = Depends(get_current_tenant_id), service: KbArticleService = Depends(get_kb_article_service),
):
    return to_dict(await service.get_or_404(tenant_id, article_id))


@router.post("/{article_id}/publish")
async def publish_article(
    article_id: str, tenant_id: str = Depends(get_current_tenant_id), service: KbArticleService = Depends(get_kb_article_service),
):
    return to_dict(await service.publish(tenant_id, article_id))


@router.post("/{article_id}/unpublish")
async def unpublish_article(
    article_id: str, tenant_id: str = Depends(get_current_tenant_id), service: KbArticleService = Depends(get_kb_article_service),
):
    return to_dict(await service.unpublish(tenant_id, article_id))


@router.post("/{article_id}/archive")
async def archive_article(
    article_id: str, tenant_id: str = Depends(get_current_tenant_id), service: KbArticleService = Depends(get_kb_article_service),
):
    return to_dict(await service.archive(tenant_id, article_id))
