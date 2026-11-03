from __future__ import annotations

from sqlalchemy import select

from collaboration_platform.models.comment import (
    CommentAttachmentModel,
    CommentEditHistoryModel,
    CommentModel,
    CommentReactionModel,
    MentionModel,
)
from collaboration_platform.repositories.base import SQLAlchemyRepository


class CommentRepository(SQLAlchemyRepository[CommentModel]):
    model = CommentModel

    async def get(self, id: str, *, include_deleted: bool = True) -> CommentModel | None:
        """Overrides the base repository's default of hiding rows with
        `is_deleted=True`. A deleted comment still needs to be
        fetchable by id (permalinks, thread rendering showing "this
        comment was deleted", edit-history lookups, and the guarded
        domain entity's own `InvalidTransitionError` on further edits
        all depend on the row still resolving) — visibility in
        *listings* is controlled explicitly per query via
        `list_for_asset`'s own `include_deleted` flag instead."""
        return await self.session.get(self.model, id)

    async def list_for_asset(self, asset_id: str, *, include_deleted: bool = False) -> list[CommentModel]:
        stmt = select(CommentModel).where(CommentModel.asset_id == asset_id)
        if not include_deleted:
            stmt = stmt.where(CommentModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_thread(self, thread_root_id: str) -> list[CommentModel]:
        stmt = select(CommentModel).where(CommentModel.thread_root_id == thread_root_id, CommentModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_pinned_for_asset(self, asset_id: str) -> list[CommentModel]:
        stmt = select(CommentModel).where(
            CommentModel.asset_id == asset_id, CommentModel.is_pinned.is_(True), CommentModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_unresolved_for_asset(self, asset_id: str) -> list[CommentModel]:
        stmt = select(CommentModel).where(
            CommentModel.asset_id == asset_id, CommentModel.is_resolved.is_(False), CommentModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class CommentReactionRepository(SQLAlchemyRepository[CommentReactionModel]):
    model = CommentReactionModel

    async def list_for_comment(self, comment_id: str) -> list[CommentReactionModel]:
        stmt = select(CommentReactionModel).where(CommentReactionModel.comment_id == comment_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_reaction(self, comment_id: str, user_id: str, emoji: str) -> CommentReactionModel | None:
        stmt = select(CommentReactionModel).where(
            CommentReactionModel.comment_id == comment_id,
            CommentReactionModel.user_id == user_id,
            CommentReactionModel.emoji == emoji,
        )
        return (await self.session.execute(stmt)).scalars().first()


class CommentAttachmentRepository(SQLAlchemyRepository[CommentAttachmentModel]):
    model = CommentAttachmentModel

    async def list_for_comment(self, comment_id: str) -> list[CommentAttachmentModel]:
        stmt = select(CommentAttachmentModel).where(CommentAttachmentModel.comment_id == comment_id)
        return list((await self.session.execute(stmt)).scalars().all())


class MentionRepository(SQLAlchemyRepository[MentionModel]):
    model = MentionModel

    async def list_for_comment(self, comment_id: str) -> list[MentionModel]:
        stmt = select(MentionModel).where(MentionModel.comment_id == comment_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_user(self, mentioned_user_id: str) -> list[MentionModel]:
        stmt = select(MentionModel).where(MentionModel.mentioned_user_id == mentioned_user_id)
        return list((await self.session.execute(stmt)).scalars().all())


class CommentEditHistoryRepository(SQLAlchemyRepository[CommentEditHistoryModel]):
    model = CommentEditHistoryModel

    async def list_for_comment(self, comment_id: str) -> list[CommentEditHistoryModel]:
        stmt = select(CommentEditHistoryModel).where(CommentEditHistoryModel.comment_id == comment_id)
        return list((await self.session.execute(stmt)).scalars().all())
