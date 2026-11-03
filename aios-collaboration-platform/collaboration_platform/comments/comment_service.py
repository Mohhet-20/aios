"""CommentService: comments and threaded discussions on an asset,
backed by the guarded `Comment` domain entity (see
`domain/entities.py`) for resolve/reopen/pin/soft-delete. Threading is
flat-with-a-root-pointer rather than deeply nested: every reply's
`thread_root_id` points at the top-level comment that started the
thread (never at its immediate parent's thread_root, to avoid a
lookup chain), which keeps "load a whole thread" a single indexed
query regardless of reply depth."""
from __future__ import annotations

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.core.exceptions import CommentTooLongError, PermissionDeniedError
from collaboration_platform.domain.entities import Comment
from collaboration_platform.models.comment import CommentEditHistoryModel, CommentModel
from collaboration_platform.repositories.registry import RepositoryRegistry


def _comment_to_domain(model: CommentModel) -> Comment:
    return Comment(
        id=model.id, body=model.body, is_resolved=model.is_resolved, is_pinned=model.is_pinned,
        is_deleted=model.is_deleted, edited_at=model.edited_at, resolved_at=model.resolved_at, deleted_at=model.deleted_at,
    )


def _apply_comment_domain(entity: Comment, model: CommentModel) -> None:
    model.body = entity.body
    model.is_resolved = entity.is_resolved
    model.is_pinned = entity.is_pinned
    model.is_deleted = entity.is_deleted
    model.edited_at = entity.edited_at
    model.resolved_at = entity.resolved_at
    model.deleted_at = entity.deleted_at


class CommentService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def add_comment(
        self, asset_id: str, author_id: str, body: str, *, parent_comment_id: str | None = None, version_id: str | None = None
    ) -> CommentModel:
        if len(body) > self.settings.comment_max_length:
            raise CommentTooLongError(f"comment exceeds max length of {self.settings.comment_max_length} characters")
        await self.repos.assets.get_or_404(asset_id)

        thread_root_id = None
        if parent_comment_id is not None:
            parent = await self.repos.comments.get_or_404(parent_comment_id)
            thread_root_id = parent.thread_root_id or parent.id

        comment = await self.repos.comments.add(CommentModel(
            asset_id=asset_id, version_id=version_id, thread_root_id=thread_root_id,
            parent_comment_id=parent_comment_id, author_id=author_id, body=body,
        ))
        if thread_root_id is None:
            # a top-level comment is the root of its own thread
            comment.thread_root_id = comment.id
            comment = await self.repos.comments.update(comment)
        return comment

    async def edit_comment(self, comment_id: str, editor_id: str, new_body: str) -> CommentModel:
        if len(new_body) > self.settings.comment_max_length:
            raise CommentTooLongError(f"comment exceeds max length of {self.settings.comment_max_length} characters")
        comment = await self.repos.comments.get_or_404(comment_id)
        if comment.author_id != editor_id:
            raise PermissionDeniedError(f"user '{editor_id}' cannot edit a comment authored by '{comment.author_id}'")
        await self.repos.comment_edit_history.add(
            CommentEditHistoryModel(comment_id=comment.id, previous_body=comment.body, edited_by=editor_id)
        )
        entity = _comment_to_domain(comment)
        entity.edit(new_body)
        _apply_comment_domain(entity, comment)
        return await self.repos.comments.update(comment)

    async def resolve_thread(self, comment_id: str, resolved_by: str) -> CommentModel:
        comment = await self.repos.comments.get_or_404(comment_id)
        entity = _comment_to_domain(comment)
        entity.resolve()
        _apply_comment_domain(entity, comment)
        return await self.repos.comments.update(comment)

    async def reopen_thread(self, comment_id: str) -> CommentModel:
        comment = await self.repos.comments.get_or_404(comment_id)
        entity = _comment_to_domain(comment)
        entity.reopen()
        _apply_comment_domain(entity, comment)
        return await self.repos.comments.update(comment)

    async def pin(self, comment_id: str) -> CommentModel:
        comment = await self.repos.comments.get_or_404(comment_id)
        entity = _comment_to_domain(comment)
        entity.pin()
        _apply_comment_domain(entity, comment)
        return await self.repos.comments.update(comment)

    async def unpin(self, comment_id: str) -> CommentModel:
        comment = await self.repos.comments.get_or_404(comment_id)
        entity = _comment_to_domain(comment)
        entity.unpin()
        _apply_comment_domain(entity, comment)
        return await self.repos.comments.update(comment)

    async def delete_comment(self, comment_id: str, requested_by: str) -> CommentModel:
        comment = await self.repos.comments.get_or_404(comment_id)
        if comment.author_id != requested_by:
            raise PermissionDeniedError(f"user '{requested_by}' cannot delete a comment authored by '{comment.author_id}'")
        entity = _comment_to_domain(comment)
        entity.soft_delete()
        _apply_comment_domain(entity, comment)
        return await self.repos.comments.update(comment)

    async def list_for_asset(self, asset_id: str) -> list[CommentModel]:
        return await self.repos.comments.list_for_asset(asset_id)

    async def list_thread(self, thread_root_id: str) -> list[CommentModel]:
        return await self.repos.comments.list_thread(thread_root_id)

    async def list_pinned(self, asset_id: str) -> list[CommentModel]:
        return await self.repos.comments.list_pinned_for_asset(asset_id)

    async def list_unresolved(self, asset_id: str) -> list[CommentModel]:
        return await self.repos.comments.list_unresolved_for_asset(asset_id)

    async def list_edit_history(self, comment_id: str) -> list[CommentEditHistoryModel]:
        return await self.repos.comment_edit_history.list_for_comment(comment_id)
