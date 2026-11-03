"""ReactionService: emoji reactions on a comment (one reaction per
user per emoji per comment — a user can react with multiple different
emoji, but not stack the same one twice)."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ConflictError, NotFoundError
from collaboration_platform.models.comment import CommentReactionModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class ReactionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_reaction(self, comment_id: str, user_id: str, emoji: str) -> CommentReactionModel:
        await self.repos.comments.get_or_404(comment_id)
        existing = await self.repos.comment_reactions.get_reaction(comment_id, user_id, emoji)
        if existing is not None:
            raise ConflictError(f"user '{user_id}' already reacted with '{emoji}' on comment '{comment_id}'")
        return await self.repos.comment_reactions.add(CommentReactionModel(comment_id=comment_id, user_id=user_id, emoji=emoji))

    async def remove_reaction(self, comment_id: str, user_id: str, emoji: str) -> None:
        existing = await self.repos.comment_reactions.get_reaction(comment_id, user_id, emoji)
        if existing is None:
            raise NotFoundError(f"no '{emoji}' reaction from '{user_id}' on comment '{comment_id}'")
        await self.repos.comment_reactions.delete(existing, hard=True)

    async def list_for_comment(self, comment_id: str) -> list[CommentReactionModel]:
        return await self.repos.comment_reactions.list_for_comment(comment_id)
