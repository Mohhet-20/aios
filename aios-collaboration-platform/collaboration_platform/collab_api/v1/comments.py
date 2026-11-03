"""Comments, threaded discussions, reactions, attachments, and
mentions."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.comments.attachment_service import AttachmentService
from collaboration_platform.comments.comment_service import CommentService
from collaboration_platform.comments.reaction_service import ReactionService
from collaboration_platform.dependencies.dependencies import (
    get_attachment_service,
    get_comment_service,
    get_mention_service,
    get_reaction_service,
)
from collaboration_platform.mentions.mention_service import MentionService

router = APIRouter(prefix="/comments", tags=["comments"])


class AddCommentRequest(BaseModel):
    asset_id: str
    author_id: str
    body: str
    parent_comment_id: str | None = None
    version_id: str | None = None


@router.post("", status_code=201)
async def add_comment(body: AddCommentRequest, service: CommentService = Depends(get_comment_service)):
    return to_dict(await service.add_comment(
        body.asset_id, body.author_id, body.body, parent_comment_id=body.parent_comment_id, version_id=body.version_id,
    ))


@router.get("/asset/{asset_id}")
async def list_comments(asset_id: str, service: CommentService = Depends(get_comment_service)):
    return to_dict_list(await service.list_for_asset(asset_id))


@router.get("/thread/{thread_root_id}")
async def list_thread(thread_root_id: str, service: CommentService = Depends(get_comment_service)):
    return to_dict_list(await service.list_thread(thread_root_id))


@router.get("/asset/{asset_id}/pinned")
async def list_pinned(asset_id: str, service: CommentService = Depends(get_comment_service)):
    return to_dict_list(await service.list_pinned(asset_id))


@router.get("/asset/{asset_id}/unresolved")
async def list_unresolved(asset_id: str, service: CommentService = Depends(get_comment_service)):
    return to_dict_list(await service.list_unresolved(asset_id))


class EditCommentRequest(BaseModel):
    editor_id: str
    new_body: str


@router.put("/{comment_id}")
async def edit_comment(comment_id: str, body: EditCommentRequest, service: CommentService = Depends(get_comment_service)):
    return to_dict(await service.edit_comment(comment_id, body.editor_id, body.new_body))


@router.get("/{comment_id}/history")
async def comment_history(comment_id: str, service: CommentService = Depends(get_comment_service)):
    return to_dict_list(await service.list_edit_history(comment_id))


@router.post("/{comment_id}/resolve")
async def resolve_thread(comment_id: str, resolved_by: str, service: CommentService = Depends(get_comment_service)):
    return to_dict(await service.resolve_thread(comment_id, resolved_by))


@router.post("/{comment_id}/reopen")
async def reopen_thread(comment_id: str, service: CommentService = Depends(get_comment_service)):
    return to_dict(await service.reopen_thread(comment_id))


@router.post("/{comment_id}/pin")
async def pin_comment(comment_id: str, service: CommentService = Depends(get_comment_service)):
    return to_dict(await service.pin(comment_id))


@router.post("/{comment_id}/unpin")
async def unpin_comment(comment_id: str, service: CommentService = Depends(get_comment_service)):
    return to_dict(await service.unpin(comment_id))


@router.delete("/{comment_id}")
async def delete_comment(comment_id: str, requested_by: str, service: CommentService = Depends(get_comment_service)):
    return to_dict(await service.delete_comment(comment_id, requested_by))


class AddReactionRequest(BaseModel):
    user_id: str
    emoji: str


@router.post("/{comment_id}/reactions", status_code=201)
async def add_reaction(comment_id: str, body: AddReactionRequest, service: ReactionService = Depends(get_reaction_service)):
    return to_dict(await service.add_reaction(comment_id, body.user_id, body.emoji))


@router.delete("/{comment_id}/reactions/{user_id}/{emoji}", status_code=204)
async def remove_reaction(comment_id: str, user_id: str, emoji: str, service: ReactionService = Depends(get_reaction_service)):
    await service.remove_reaction(comment_id, user_id, emoji)


@router.get("/{comment_id}/reactions")
async def list_reactions(comment_id: str, service: ReactionService = Depends(get_reaction_service)):
    return to_dict_list(await service.list_for_comment(comment_id))


class AddAttachmentRequest(BaseModel):
    file_name: str
    content_ref: str
    uploaded_by: str
    content_type: str | None = None


@router.post("/{comment_id}/attachments", status_code=201)
async def add_attachment(comment_id: str, body: AddAttachmentRequest, service: AttachmentService = Depends(get_attachment_service)):
    return to_dict(await service.add_attachment(
        comment_id, file_name=body.file_name, content_ref=body.content_ref, uploaded_by=body.uploaded_by, content_type=body.content_type,
    ))


@router.get("/{comment_id}/attachments")
async def list_attachments(comment_id: str, service: AttachmentService = Depends(get_attachment_service)):
    return to_dict_list(await service.list_for_comment(comment_id))


class CreateMentionsRequest(BaseModel):
    mentioned_user_ids: list[str]


@router.post("/{comment_id}/mentions", status_code=201)
async def create_mentions(comment_id: str, body: CreateMentionsRequest, service: MentionService = Depends(get_mention_service)):
    return to_dict_list(await service.create_mentions(comment_id, body.mentioned_user_ids))


@router.get("/{comment_id}/mentions")
async def list_mentions(comment_id: str, service: MentionService = Depends(get_mention_service)):
    return to_dict_list(await service.list_for_comment(comment_id))


@router.get("/mentions/user/{user_id}")
async def list_mentions_for_user(user_id: str, service: MentionService = Depends(get_mention_service)):
    return to_dict_list(await service.list_for_user(user_id))
