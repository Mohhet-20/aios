"""ORM models for comments, threaded discussions, reactions,
attachments, mentions, and comment edit history."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow


class CommentModel(IdMixin, Base):
    __tablename__ = "cp_comments"
    __table_args__ = (
        Index("ix_cp_comments_asset", "asset_id"),
        Index("ix_cp_comments_thread", "thread_root_id"),
        Index("ix_cp_comments_parent", "parent_comment_id"),
    )

    asset_id: Mapped[str] = mapped_column(ForeignKey("cp_assets.id"), nullable=False)
    version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    thread_root_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    parent_comment_id: Mapped[str | None] = mapped_column(ForeignKey("cp_comments.id"), nullable=True)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommentReactionModel(IdMixin, Base):
    __tablename__ = "cp_comment_reactions"
    __table_args__ = (UniqueConstraint("comment_id", "user_id", "emoji", name="uq_cp_comment_reaction"),)

    comment_id: Mapped[str] = mapped_column(ForeignKey("cp_comments.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    emoji: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CommentAttachmentModel(IdMixin, Base):
    __tablename__ = "cp_comment_attachments"

    comment_id: Mapped[str] = mapped_column(ForeignKey("cp_comments.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MentionModel(IdMixin, Base):
    __tablename__ = "cp_mentions"
    __table_args__ = (Index("ix_cp_mentions_user", "mentioned_user_id"),)

    comment_id: Mapped[str] = mapped_column(ForeignKey("cp_comments.id"), nullable=False, index=True)
    mentioned_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CommentEditHistoryModel(IdMixin, Base):
    __tablename__ = "cp_comment_edit_history"

    comment_id: Mapped[str] = mapped_column(ForeignKey("cp_comments.id"), nullable=False, index=True)
    previous_body: Mapped[str] = mapped_column(Text, nullable=False)
    edited_by: Mapped[str] = mapped_column(String(36), nullable=False)
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
