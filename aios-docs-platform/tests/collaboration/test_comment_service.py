import pytest

from docs_platform.collaboration.comment_service import CommentService

pytestmark = pytest.mark.asyncio

TENANT = "t-collab"


async def test_add_and_resolve_comment(repos):
    svc = CommentService(repos)
    comment = await svc.add_comment(TENANT, target_ref="page:1", author_id="u1", body="typo here")
    assert comment.resolved is False
    resolved = await svc.resolve_comment(TENANT, comment.id)
    assert resolved.resolved is True


async def test_list_for_target(repos):
    svc = CommentService(repos)
    await svc.add_comment(TENANT, target_ref="page:2", author_id="u1", body="first")
    await svc.add_comment(TENANT, target_ref="page:2", author_id="u2", body="second")
    await svc.add_comment(TENANT, target_ref="page:3", author_id="u1", body="unrelated")
    comments = await svc.list_for_target(TENANT, "page:2")
    assert len(comments) == 2
