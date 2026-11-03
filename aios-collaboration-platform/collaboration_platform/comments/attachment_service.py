"""AttachmentService: files/code-snippet blobs attached to a comment.
Like the Identity Platform's approach to secrets, this platform stores
only a reference (`content_ref` — a URL or blob-store key) and never
the raw bytes; upload/storage is out of scope for the collaboration
layer, whose job is just tracking what's attached to what."""
from __future__ import annotations

from collaboration_platform.models.comment import CommentAttachmentModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class AttachmentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_attachment(
        self, comment_id: str, *, file_name: str, content_ref: str, uploaded_by: str, content_type: str | None = None
    ) -> CommentAttachmentModel:
        await self.repos.comments.get_or_404(comment_id)
        return await self.repos.comment_attachments.add(CommentAttachmentModel(
            comment_id=comment_id, file_name=file_name, content_type=content_type,
            content_ref=content_ref, uploaded_by=uploaded_by,
        ))

    async def list_for_comment(self, comment_id: str) -> list[CommentAttachmentModel]:
        return await self.repos.comment_attachments.list_for_comment(comment_id)
