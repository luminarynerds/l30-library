# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron blog bookmark endpoints.

Lives in a separate file from ``blog.py`` to avoid merge conflicts with the
in-flight PR #1140 (blog refactor). Router is mounted alongside the existing
blog router from ``registry.py``.

All endpoints require an authenticated user (patron auth) and operate on the
current user's bookmarks only.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.blog import BlogPost, BlogPostStatus
from app.models.blog_bookmark import BlogPostBookmark
from app.models.user import User
from app.schemas.blog import (
    BlogBookmarkCreateResponse,
    BlogPostBookmarkedResponse,
)

from .auth import get_current_user

router = APIRouter(prefix="/blog/bookmarks", tags=["blog-bookmarks"])


@router.get("", response_model=List[BlogPostBookmarkedResponse])
async def list_my_bookmarks(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[BlogPostBookmarkedResponse]:
    """List current user's bookmarked blog posts, newest bookmark first."""
    user_id = current_user.id
    result = await db.execute(
        select(BlogPostBookmark, BlogPost)
        .join(BlogPost, BlogPost.id == BlogPostBookmark.post_id)
        .where(BlogPostBookmark.user_id == user_id)
        .order_by(BlogPostBookmark.created_at.desc(), BlogPostBookmark.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()

    out: list[BlogPostBookmarkedResponse] = []
    for bookmark, post in rows:
        post_data = BlogPostBookmarkedResponse.model_validate(
            {
                **{
                    col.name: getattr(post, col.name)
                    for col in post.__table__.columns
                },
                "tags": [],
                "bookmarked_at": bookmark.created_at,
            }
        )
        out.append(post_data)
    return out


@router.post(
    "/{post_id}",
    response_model=BlogBookmarkCreateResponse,
    status_code=status.HTTP_200_OK,
)
async def add_bookmark(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlogBookmarkCreateResponse:
    """Add a bookmark for the current user. Idempotent.

    Returns 200 with ``already_bookmarked=True`` if the user had already
    bookmarked the post, else 200 with a fresh row and ``already_bookmarked=False``.

    Returns 404 if the post does not exist or is not published.
    """
    # Snapshot scalar attrs up-front so the IntegrityError-recovery path
    # never has to re-fetch them from an expired ORM state (which would
    # require a working session and re-raise after rollback).
    user_id = current_user.id

    # Only published posts are bookmarkable; missing/draft/scheduled -> 404.
    post_result = await db.execute(
        select(BlogPost).where(
            BlogPost.id == post_id,
            BlogPost.status == BlogPostStatus.published,
        )
    )
    post = post_result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Blog post not found")

    # Insert-then-catch keeps it race-safe under concurrent POSTs.
    bookmark = BlogPostBookmark(user_id=user_id, post_id=post_id)
    db.add(bookmark)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing_result = await db.execute(
            select(BlogPostBookmark).where(
                BlogPostBookmark.user_id == user_id,
                BlogPostBookmark.post_id == post_id,
            )
        )
        existing = existing_result.scalar_one()
        return BlogBookmarkCreateResponse(
            post_id=existing.post_id,
            created_at=existing.created_at,
            already_bookmarked=True,
        )

    await db.refresh(bookmark)
    return BlogBookmarkCreateResponse(
        post_id=bookmark.post_id,
        created_at=bookmark.created_at,
        already_bookmarked=False,
    )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Remove a bookmark. 204 on success, 404 if not bookmarked."""
    user_id = current_user.id
    result = await db.execute(
        select(BlogPostBookmark).where(
            BlogPostBookmark.user_id == user_id,
            BlogPostBookmark.post_id == post_id,
        )
    )
    bookmark = result.scalar_one_or_none()
    if bookmark is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    await db.delete(bookmark)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
