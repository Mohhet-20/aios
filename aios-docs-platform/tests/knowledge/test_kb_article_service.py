import pytest

from docs_platform.core.exceptions import InvalidTransitionError, UnsupportedKbArticleTypeError
from docs_platform.knowledge.kb_article_service import KbArticleService

pytestmark = pytest.mark.asyncio

TENANT = "t-kb"


async def test_create_article_rejects_unsupported_type(repos):
    svc = KbArticleService(repos)
    with pytest.raises(UnsupportedKbArticleTypeError):
        await svc.create_article(TENANT, article_type="not-a-type", title="X", slug="x")


async def test_lifecycle_draft_to_published_to_archived(repos):
    svc = KbArticleService(repos)
    article = await svc.create_article(TENANT, article_type="how_to", title="Deploy AIOS", slug="deploy-aios", tags=["deploy", "ops"])
    assert article.status == "draft"

    published = await svc.publish(TENANT, article.id)
    assert published.status == "published"

    unpublished = await svc.unpublish(TENANT, article.id)
    assert unpublished.status == "draft"

    republished = await svc.publish(TENANT, article.id)
    archived = await svc.archive(TENANT, republished.id)
    assert archived.status == "archived"

    with pytest.raises(InvalidTransitionError):
        await svc.publish(TENANT, article.id)


async def test_list_by_tag(repos):
    svc = KbArticleService(repos)
    await svc.create_article(TENANT, article_type="faq", title="FAQ 1", slug="faq-1", tags=["billing"])
    await svc.create_article(TENANT, article_type="faq", title="FAQ 2", slug="faq-2", tags=["security"])
    billing = await svc.list_by_tag(TENANT, "billing")
    assert len(billing) == 1
    assert billing[0].slug == "faq-1"


async def test_list_articles_filters_by_type_and_status(repos):
    svc = KbArticleService(repos)
    a = await svc.create_article(TENANT, article_type="glossary", title="Glossary", slug="glossary")
    await svc.publish(TENANT, a.id)
    await svc.create_article(TENANT, article_type="glossary", title="Draft Glossary", slug="draft-glossary")

    published_glossary = await svc.list_articles(TENANT, article_type="glossary", status="published")
    assert len(published_glossary) == 1
    assert published_glossary[0].slug == "glossary"
