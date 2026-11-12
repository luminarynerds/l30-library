# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Indie author follow endpoints -- patron follows an indie author."""
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.indie_author import IndieAuthor
from ...models.indie_author_follow import IndieAuthorFollow
from ...models.user import User
from ..v1.auth import get_current_user, get_optional_user

logger = get_logger(__name__)

router = APIRouter(prefix="/indie/authors", tags=["indie-author-follow"])


class FollowStatus(BaseModel):
    indie_author_id: int
    following: bool
    follower_count: int


class FollowedAuthor(BaseModel):
    indie_author_id: int
    pen_name: str | None
    profile_image_url: str | None
    followed_at: str


@router.get("/{author_id}/follow", response_model=FollowStatus)
async def get_follow_status(
    author_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Whether the current user follows this indie author, plus total followers.

    Anonymous callers always get following=false; follower_count is always public.
    """
    author_row = await db.execute(
        select(IndieAuthor.id).where(IndieAuthor.id == author_id)
    )
    if author_row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    following = False
    if current_user is not None:
        existing = await db.execute(
            select(IndieAuthorFollow.id).where(
                IndieAuthorFollow.user_id == current_user.id,
                IndieAuthorFollow.indie_author_id == author_id,
            )
        )
        following = existing.scalar_one_or_none() is not None

    count_row = await db.execute(
        select(IndieAuthorFollow.id).where(
            IndieAuthorFollow.indie_author_id == author_id
        )
    )
    follower_count = len(count_row.scalars().all())

    return FollowStatus(
        indie_author_id=author_id,
        following=following,
        follower_count=follower_count,
    )


@router.post(
    "/{author_id}/follow",
    response_model=FollowStatus,
    status_code=status.HTTP_201_CREATED,
)
async def follow_indie_author(
    author_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Follow an indie author. Idempotent -- repeats return 200-ish without error."""
    author_row = await db.execute(
        select(IndieAuthor.id).where(IndieAuthor.id == author_id)
    )
    if author_row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    existing = await db.execute(
        select(IndieAuthorFollow).where(
            IndieAuthorFollow.user_id == current_user.id,
            IndieAuthorFollow.indie_author_id == author_id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(
            IndieAuthorFollow(user_id=current_user.id, indie_author_id=author_id)
        )
        await db.commit()

    count_row = await db.execute(
        select(IndieAuthorFollow.id).where(
            IndieAuthorFollow.indie_author_id == author_id
        )
    )
    follower_count = len(count_row.scalars().all())

    return FollowStatus(
        indie_author_id=author_id,
        following=True,
        follower_count=follower_count,
    )


@router.delete("/{author_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_indie_author(
    author_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unfollow an indie author. Idempotent."""
    result = await db.execute(
        select(IndieAuthorFollow).where(
            IndieAuthorFollow.user_id == current_user.id,
            IndieAuthorFollow.indie_author_id == author_id,
        )
    )
    follow = result.scalar_one_or_none()
    if follow is not None:
        await db.delete(follow)
        await db.commit()


@router.get("/me/follows", response_model=list[FollowedAuthor])
async def list_my_indie_follows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Authors the current user follows, most recently followed first."""
    stmt = (
        select(IndieAuthorFollow, IndieAuthor)
        .join(IndieAuthor, IndieAuthorFollow.indie_author_id == IndieAuthor.id)
        .where(IndieAuthorFollow.user_id == current_user.id)
        .order_by(IndieAuthorFollow.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        FollowedAuthor(
            indie_author_id=author.id,
            pen_name=author.pen_name,
            profile_image_url=author.profile_image_url,
            followed_at=follow.created_at.isoformat() if follow.created_at else "",
        )
        for follow, author in rows
    ]
