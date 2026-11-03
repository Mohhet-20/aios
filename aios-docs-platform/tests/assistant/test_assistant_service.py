import datetime as dt

import pytest

from docs_platform.assistant.assistant_service import AssistantService
from docs_platform.documentation.doc_page_service import DocPageService
from docs_platform.documentation.doc_space_service import DocSpaceService
from docs_platform.knowledge.kb_article_service import KbArticleService

pytestmark = pytest.mark.asyncio

TENANT = "t-assistant"


async def _make_published_page(repos, *, slug, title, content):
    space = await DocSpaceService(repos).register_space(TENANT, key=f"space-{slug}", name="Space", doc_type="developer")
    pages = DocPageService(repos)
    page = await pages.create_page(TENANT, space.id, title=title, slug=slug, doc_type="developer", content=content)
    await pages.submit_for_review(TENANT, page.id)
    return await pages.publish(TENANT, page.id)


async def test_ask_returns_confident_answer_for_strong_match(repos):
    await _make_published_page(
        repos, slug="deploy-workflow", title="Deploying a Workflow",
        content="To deploy a workflow, register it with the Workflow Engine and activate the deployment.",
    )
    svc = AssistantService(repos)
    session = await svc.ask(TENANT, "deploy workflow engine")
    assert session.answer is not None
    assert session.confidence is not None
    assert session.confidence >= svc.settings.assistant_confidence_threshold
    assert any(ref.startswith("page:") for ref in session.related_doc_refs)


async def test_ask_reports_no_confident_answer_when_nothing_matches(repos):
    svc = AssistantService(repos)
    session = await svc.ask(TENANT, "completely unrelated gibberish query xyz")
    assert session.answer is None
    assert session.confidence is None


async def test_suggest_related_excludes_source_doc(repos):
    page_a = await _make_published_page(repos, slug="topic-a", title="Topic A", content="workflow deployment steps and configuration")
    await _make_published_page(repos, slug="topic-b", title="Topic B", content="workflow deployment configuration guide")
    svc = AssistantService(repos)
    related = await svc.suggest_related(TENANT, f"page:{page_a.id}")
    assert all(ref != f"page:{page_a.id}" for ref, _ in related)


async def test_find_troubleshooting_only_matches_troubleshooting_type(repos):
    kb = KbArticleService(repos)
    ts_article = await kb.create_article(TENANT, article_type="troubleshooting", title="Connection refused", slug="conn-refused", content="fix connection refused errors")
    await kb.publish(TENANT, ts_article.id)
    faq = await kb.create_article(TENANT, article_type="faq", title="Connection refused FAQ", slug="conn-refused-faq", content="connection refused questions")
    await kb.publish(TENANT, faq.id)

    svc = AssistantService(repos)
    results = await svc.find_troubleshooting(TENANT, "connection refused")
    assert all(ref == f"kb:{ts_article.id}" for ref, _ in results)


async def test_detect_outdated_pages(repos):
    fresh = await _make_published_page(repos, slug="fresh-page", title="Fresh", content="up to date content")
    stale = await _make_published_page(repos, slug="stale-page", title="Stale", content="old content")

    stale_row = await repos.doc_pages.get(stale.id)
    stale_row.last_reviewed_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=400)
    await repos.doc_pages.update(stale_row)

    svc = AssistantService(repos)
    outdated = await svc.detect_outdated_pages(TENANT)
    outdated_ids = {p.id for p in outdated}
    assert stale.id in outdated_ids
    assert fresh.id not in outdated_ids


async def test_generate_code_example_known_and_unknown_language():
    svc = AssistantService(repos=None)
    py_example = svc.generate_code_example("python", "workflows.create")
    assert "workflows.create" in py_example
    unknown = svc.generate_code_example("cobol", "workflows.create")
    assert "cobol" in unknown
