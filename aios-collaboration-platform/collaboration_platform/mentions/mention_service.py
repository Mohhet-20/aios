"""MentionService: records who was @mentioned in a comment. Mention
extraction (parsing `@username` out of comment text) is a client/UI
concern — the backend accepts an already-resolved list of user ids so
it never has to guess at username-to-id resolution or handle
ambiguous/partial matches."""
from __future__ import annotations

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.core.exceptions import ValidationError
from collaboration_platform.models.comment import MentionModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class MentionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_mentions(self, comment_id: str, mentioned_user_ids: list[str]) -> list[MentionModel]:
        await self.repos.comments.get_or_404(comment_id)
        unique_ids = list(dict.fromkeys(mentioned_user_ids))  # de-dupe, preserve order
        if len(unique_ids) > self.settings.max_mentions_per_comment:
            raise ValidationError(
                f"comment '{comment_id}' has {len(unique_ids)} mentions, exceeding the limit of "
                f"{self.settings.max_mentions_per_comment}"
            )
        created = []
        for user_id in unique_ids:
            created.append(await self.repos.mentions.add(MentionModel(comment_id=comment_id, mentioned_user_id=user_id)))
        return created

    async def list_for_comment(self, comment_id: str) -> list[MentionModel]:
        return await self.repos.mentions.list_for_comment(comment_id)

    async def list_for_user(self, mentioned_user_id: str) -> list[MentionModel]:
        return await self.repos.mentions.list_for_user(mentioned_user_id)
