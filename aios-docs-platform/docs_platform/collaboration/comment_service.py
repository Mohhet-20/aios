"""Collaboration: inline comments/suggestions against any target
(a doc page, a KB article, a tutorial — `target_ref` is a generic
"kind:id" reference, not a foreign key, so comments work uniformly
across every commentable resource in this platform)."""
from __future__ import annotations

from docs_platform.core.exceptions import CommentNotFoundError
from docs_platform.models.collaboration import CommentModel
from docs_platform.repositories.registry import RepositoryRegistry


class CommentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_or_404(self, tenant_id: str, comment_id: str) -> CommentModel:
        comment = await self.repos.comments.get_or_404(comment_id)
        if comment.tenant_id != tenant_id:
            raise CommentNotFoundError(f"Comment '{comment_id}' not found for tenant '{tenant_id}'")
        return comment

    async def add_comment(self, tenant_id: str, *, target_ref: str, author_id: str, body: str) -> CommentModel:
        comment = CommentModel(tenant_id=tenant_id, target_ref=target_ref, author_id=author_id, body=body)
        return await self.repos.comments.add(comment)

    async def resolve_comment(self, tenant_id: str, comment_id: str) -> CommentModel:
        comment = await self.get_or_404(tenant_id, comment_id)
        comment.resolved = True
        return await self.repos.comments.update(comment)

    async def list_for_target(self, tenant_id: str, target_ref: str) -> list[CommentModel]:
        return await self.repos.comments.list_for_target(tenant_id, target_ref)
