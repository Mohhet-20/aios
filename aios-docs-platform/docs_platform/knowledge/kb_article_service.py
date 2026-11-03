"""Knowledge Base: articles across the nine types the prompt specifies
(how-to, best practice, troubleshooting, FAQ, release note, migration
guide, design pattern, reference, glossary). Status is a simple field
guarded directly here rather than through a dedicated domain entity —
its draft -> published -> archived shape (plus published -> draft to
unpublish for further edits) carries no extra domain logic beyond the
three states themselves, the same "simple status field" precedent
used throughout this platform family."""
from __future__ import annotations

from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import InvalidTransitionError, KbArticleNotFoundError, UnsupportedKbArticleTypeError
from docs_platform.domain.enums import KbArticleStatus
from docs_platform.models.knowledge_base import KbArticleModel
from docs_platform.repositories.registry import RepositoryRegistry

_KB_TRANSITIONS: dict[KbArticleStatus, set[KbArticleStatus]] = {
    KbArticleStatus.DRAFT: {KbArticleStatus.PUBLISHED},
    KbArticleStatus.PUBLISHED: {KbArticleStatus.ARCHIVED, KbArticleStatus.DRAFT},
    KbArticleStatus.ARCHIVED: set(),
}


class KbArticleService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, article_id: str) -> KbArticleModel:
        article = await self.repos.kb_articles.get_or_404(article_id)
        if article.tenant_id != tenant_id:
            raise KbArticleNotFoundError(f"KB article '{article_id}' not found for tenant '{tenant_id}'")
        return article

    async def create_article(
        self, tenant_id: str, *, article_type: str, title: str, slug: str, content: str = "",
        tags: list[str] | None = None, owner_id: str | None = None,
    ) -> KbArticleModel:
        if article_type not in self.settings.kb_article_types:
            raise UnsupportedKbArticleTypeError(f"Unsupported KB article type '{article_type}'")
        article = KbArticleModel(
            tenant_id=tenant_id, article_type=article_type, title=title, slug=slug, content=content,
            tags=tags or [], owner_id=owner_id, status=KbArticleStatus.DRAFT.value,
        )
        return await self.repos.kb_articles.add(article)

    async def _transition(self, tenant_id: str, article_id: str, target: KbArticleStatus) -> KbArticleModel:
        article = await self.get_or_404(tenant_id, article_id)
        current = KbArticleStatus(article.status)
        if target not in _KB_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(f"KbArticle '{article_id}' cannot transition from {current.value} to {target.value}")
        article.status = target.value
        return await self.repos.kb_articles.update(article)

    async def publish(self, tenant_id: str, article_id: str) -> KbArticleModel:
        return await self._transition(tenant_id, article_id, KbArticleStatus.PUBLISHED)

    async def unpublish(self, tenant_id: str, article_id: str) -> KbArticleModel:
        return await self._transition(tenant_id, article_id, KbArticleStatus.DRAFT)

    async def archive(self, tenant_id: str, article_id: str) -> KbArticleModel:
        return await self._transition(tenant_id, article_id, KbArticleStatus.ARCHIVED)

    async def list_articles(self, tenant_id: str, *, article_type: str | None = None, status: str | None = None) -> list[KbArticleModel]:
        return await self.repos.kb_articles.list_for_tenant(tenant_id, article_type=article_type, status=status)

    async def list_by_tag(self, tenant_id: str, tag: str) -> list[KbArticleModel]:
        articles = await self.list_articles(tenant_id)
        return [a for a in articles if tag in a.tags]
