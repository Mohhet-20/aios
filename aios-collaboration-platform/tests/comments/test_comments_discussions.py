"""Comments, threading, reactions, attachments, mentions, edit
history, resolve/pin/delete lifecycle tests."""
from __future__ import annotations

import pytest

from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.comments.attachment_service import AttachmentService
from collaboration_platform.comments.comment_service import CommentService
from collaboration_platform.comments.reaction_service import ReactionService
from collaboration_platform.config.settings import Settings
from collaboration_platform.core.exceptions import (
    CommentTooLongError,
    ConflictError,
    InvalidTransitionError,
    PermissionDeniedError,
    ThreadAlreadyResolvedError,
    ValidationError,
)
from collaboration_platform.domain.enums import AssetType
from collaboration_platform.mentions.mention_service import MentionService
from collaboration_platform.workspace.workspace_service import WorkspaceService


async def _make_asset(repos, name="Asset"):
    ws = await WorkspaceService(repos).create_workspace(name=f"WS-{name}", owner_id="user-1")
    return await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.PROMPT, external_ref_id=f"ext-{name}", name=name, owner_id="user-1"
    )


@pytest.mark.asyncio
async def test_threaded_comments_share_root(repos):
    asset = await _make_asset(repos, "thread")
    svc = CommentService(repos)
    root = await svc.add_comment(asset.id, "user-1", "Top level comment")
    assert root.thread_root_id == root.id

    reply1 = await svc.add_comment(asset.id, "user-2", "Reply one", parent_comment_id=root.id)
    reply2 = await svc.add_comment(asset.id, "user-3", "Reply two", parent_comment_id=reply1.id)
    assert reply1.thread_root_id == root.id
    assert reply2.thread_root_id == root.id  # points at the thread root, not its immediate parent

    thread = await svc.list_thread(root.id)
    # list_thread filters on thread_root_id, and the root's own thread_root_id
    # points at itself, so it's included alongside its two replies.
    assert len(thread) == 3
    assert {c.id for c in thread} == {root.id, reply1.id, reply2.id}


@pytest.mark.asyncio
async def test_comment_too_long_rejected(repos):
    asset = await _make_asset(repos, "toolong")
    settings = Settings(secret_key="x" * 32, comment_max_length=10)
    svc = CommentService(repos, settings=settings)
    with pytest.raises(CommentTooLongError):
        await svc.add_comment(asset.id, "user-1", "this comment body is way too long")


@pytest.mark.asyncio
async def test_edit_only_by_author_and_records_history(repos):
    asset = await _make_asset(repos, "edit")
    svc = CommentService(repos)
    comment = await svc.add_comment(asset.id, "user-1", "original text")

    with pytest.raises(PermissionDeniedError):
        await svc.edit_comment(comment.id, "user-2", "hijacked edit")

    edited = await svc.edit_comment(comment.id, "user-1", "updated text")
    assert edited.body == "updated text"
    assert edited.edited_at is not None
    history = await svc.list_edit_history(comment.id)
    assert len(history) == 1
    assert history[0].previous_body == "original text"


@pytest.mark.asyncio
async def test_resolve_pin_delete_lifecycle(repos):
    asset = await _make_asset(repos, "lifecycle")
    svc = CommentService(repos)
    comment = await svc.add_comment(asset.id, "user-1", "needs review")

    resolved = await svc.resolve_thread(comment.id, resolved_by="user-2")
    assert resolved.is_resolved is True
    with pytest.raises(ThreadAlreadyResolvedError):
        await svc.resolve_thread(comment.id, resolved_by="user-2")

    reopened = await svc.reopen_thread(comment.id)
    assert reopened.is_resolved is False

    pinned = await svc.pin(comment.id)
    assert pinned.is_pinned is True
    assert len(await svc.list_pinned(asset.id)) == 1

    deleted = await svc.delete_comment(comment.id, requested_by="user-1")
    assert deleted.is_deleted is True
    with pytest.raises(InvalidTransitionError):
        await svc.edit_comment(comment.id, "user-1", "cant edit deleted")


@pytest.mark.asyncio
async def test_reactions_unique_per_user_emoji(repos):
    asset = await _make_asset(repos, "reactions")
    comment = await CommentService(repos).add_comment(asset.id, "user-1", "nice work")
    reaction_svc = ReactionService(repos)
    await reaction_svc.add_reaction(comment.id, "user-2", "👍")
    with pytest.raises(ConflictError):
        await reaction_svc.add_reaction(comment.id, "user-2", "👍")
    await reaction_svc.add_reaction(comment.id, "user-2", "🎉")  # different emoji is fine
    assert len(await reaction_svc.list_for_comment(comment.id)) == 2
    await reaction_svc.remove_reaction(comment.id, "user-2", "👍")
    assert len(await reaction_svc.list_for_comment(comment.id)) == 1


@pytest.mark.asyncio
async def test_attachments_and_mentions(repos):
    asset = await _make_asset(repos, "attach")
    comment = await CommentService(repos).add_comment(asset.id, "user-1", "see attached, cc @bob @carol")

    attachment_svc = AttachmentService(repos)
    await attachment_svc.add_attachment(comment.id, file_name="notes.txt", content_ref="blob://abc", uploaded_by="user-1")
    assert len(await attachment_svc.list_for_comment(comment.id)) == 1

    settings = Settings(secret_key="x" * 32, max_mentions_per_comment=2)
    mention_svc = MentionService(repos, settings=settings)
    await mention_svc.create_mentions(comment.id, ["user-bob", "user-carol"])
    assert len(await mention_svc.list_for_comment(comment.id)) == 2

    with pytest.raises(ValidationError):
        await mention_svc.create_mentions(comment.id, ["u1", "u2", "u3"])
