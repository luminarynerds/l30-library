# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import enum
from enum import StrEnum
import math
import re

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BlogPostStatus(StrEnum):
    draft = "draft"
    published = "published"
    scheduled = "scheduled"


# M2M join table for additional (co-)authors on a blog post.
# `author_id` on BlogPost identifies the primary author; this table
# attaches zero or more additional User rows. Kept separate from the
# tags pattern (which has its own BlogPostTag model) because we don't
# need extra columns on the link.
blog_post_co_authors = Table(
    "blog_post_co_authors",
    Base.metadata,
    Column(
        "post_id",
        Integer,
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), unique=True, nullable=False, index=True)
    body = Column(Text, nullable=False, default="")
    tldr = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    featured_image = Column(String(500), nullable=True)
    # Legacy free-text byline fields. Kept for backward compatibility +
    # fallback rendering when author_id is null. Do NOT drop these
    # without a follow-up backfill-confidence PR.
    author_name = Column(String(255), nullable=False, default="")
    author_role = Column(String(255), nullable=True)
    # Structured byline: FK to the authoring User. When set, the
    # response byline is computed from User.full_name + role; otherwise
    # falls back to author_name/author_role above.
    author_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(
        SQLEnum(BlogPostStatus, name="blog_post_status_enum", native_enum=False),
        default=BlogPostStatus.draft,
        nullable=False,
        index=True,
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    series_name = Column(String(255), nullable=True, index=True)
    series_order = Column(Integer, nullable=True)
    read_time_minutes = Column(Integer, nullable=False, default=1)
    view_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    tags = relationship("BlogTag", secondary="blog_post_tags", back_populates="posts")
    # lazy="selectin" on both author + co_authors to avoid the
    # MissingGreenlet landmine when Pydantic serializes a BlogPost
    # outside an async-context-aware lazy loader. Pass foreign_keys=
    # explicitly because User has many incoming FKs.
    author = relationship("User", foreign_keys=[author_id], lazy="selectin")
    co_authors = relationship(
        "User",
        secondary=blog_post_co_authors,
        lazy="selectin",
    )

    def calculate_read_time(self) -> int:
        if not self.body:
            return 1
        text = re.sub(r"<[^>]+>", "", self.body)
        word_count = len(text.split())
        return max(1, math.ceil(word_count / 238))


class BlogTag(Base):
    __tablename__ = "blog_tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)

    posts = relationship("BlogPost", secondary="blog_post_tags", back_populates="tags")


class BlogPostTag(Base):
    __tablename__ = "blog_post_tags"

    post_id = Column(Integer, ForeignKey("blog_posts.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("blog_tags.id", ondelete="CASCADE"), primary_key=True)


class BlogPostView(Base):
    __tablename__ = "blog_post_views"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    viewer_hash = Column(String(64), nullable=True)  # SHA256 of IP+UA for dedup, not storing raw IP
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    post = relationship("BlogPost", backref="views")


class BlogPostVersion(Base):
    __tablename__ = "blog_post_versions"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, default="")
    tldr = Column(Text, nullable=True)
    version_number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255), nullable=True)

    post = relationship("BlogPost", backref="versions")
