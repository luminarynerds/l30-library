# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff Message Board API Endpoints

Internal forum / virtual break room for library staff.
Supports posts with categories (memos, library happenings, state news, etc.),
replies, pinning, and archiving.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.staff_message_board import (
    BoardPost,
    BoardReply,
    MessageBoardCategory,
)
from ...models.user import User
from .dependencies import require_staff

router = APIRouter(prefix="/staff/message-board", tags=["staff-message-board"])


# ============================================================================
# Schemas
# ============================================================================


class AuthorResponse(BaseModel):
    id: int
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class ReplyResponse(BaseModel):
    id: int
    content: str
    author: Optional[AuthorResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    pinned: bool
    archived: bool
    author: Optional[AuthorResponse] = None
    reply_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostDetailResponse(PostResponse):
    replies: List[ReplyResponse] = []


class PostListResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1, max_length=50000)
    category: str = Field(default="general")
    pinned: bool = False


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    content: Optional[str] = Field(default=None, min_length=1, max_length=50000)
    category: Optional[str] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None


class ReplyCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class ReplyUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


# ============================================================================
# Helper
# ============================================================================


def _post_to_response(post: BoardPost, reply_count: int = 0) -> PostResponse:
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        category=post.category.value if isinstance(post.category, MessageBoardCategory) else post.category,
        pinned=post.pinned,
        archived=post.archived,
        author=AuthorResponse(id=post.author.id, full_name=post.author.full_name) if post.author else None,
        reply_count=reply_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


def _post_to_detail(post: BoardPost) -> PostDetailResponse:
    replies = [
        ReplyResponse(
            id=r.id,
            content=r.content,
            author=AuthorResponse(id=r.author.id, full_name=r.author.full_name) if r.author else None,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in (post.replies or [])
    ]
    return PostDetailResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        category=post.category.value if isinstance(post.category, MessageBoardCategory) else post.category,
        pinned=post.pinned,
        archived=post.archived,
        author=AuthorResponse(id=post.author.id, full_name=post.author.full_name) if post.author else None,
        reply_count=len(replies),
        created_at=post.created_at,
        updated_at=post.updated_at,
        replies=replies,
    )


# ============================================================================
# Post Endpoints
# ============================================================================


@router.get("/categories")
async def list_categories(
    _: User = Depends(require_staff),
) -> List[dict]:
    """List all available post categories."""
    labels = {
        "memo": "Memos",
        "library_happenings": "Library Happenings",
        "state_news": "State News",
        "general": "General Discussion",
        "tips_tricks": "Tips & Tricks",
        "professional_dev": "Professional Development",
    }
    return [{"value": c.value, "label": labels.get(c.value, c.value)} for c in MessageBoardCategory]


@router.get("", response_model=PostListResponse)
async def list_posts(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    pinned_only: bool = Query(default=False, description="Show only pinned posts"),
    include_archived: bool = Query(default=False, description="Include archived posts"),
    search: Optional[str] = Query(default=None, description="Search in title and content"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> PostListResponse:
    """List message board posts with filtering and pagination."""
    # Build query
    query = select(BoardPost).options(selectinload(BoardPost.author))

    if not include_archived:
        query = query.where(BoardPost.archived == False)
    if category:
        query = query.where(BoardPost.category == category)
    if pinned_only:
        query = query.where(BoardPost.pinned == True)
    if search:
        escaped_search = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        search_term = f"%{escaped_search}%"
        query = query.where(
            BoardPost.title.ilike(search_term) | BoardPost.content.ilike(search_term)
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate — pinned posts first, then newest
    query = query.order_by(BoardPost.pinned.desc(), BoardPost.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    posts = result.scalars().all()

    # Get reply counts
    post_ids = [p.id for p in posts]
    reply_counts: dict = {}
    if post_ids:
        rc_query = (
            select(BoardReply.post_id, func.count(BoardReply.id))
            .where(BoardReply.post_id.in_(post_ids))
            .group_by(BoardReply.post_id)
        )
        rc_result = await db.execute(rc_query)
        reply_counts = dict(rc_result.all())

    pages = max(1, (total + per_page - 1) // per_page)
    return PostListResponse(
        posts=[_post_to_response(p, reply_counts.get(p.id, 0)) for p in posts],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("", response_model=PostDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_in: PostCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> PostDetailResponse:
    """Create a new message board post."""
    # Validate category
    valid_categories = [c.value for c in MessageBoardCategory]
    if post_in.category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}",
        )

    post = BoardPost(
        title=post_in.title,
        content=post_in.content,
        category=post_in.category,
        pinned=post_in.pinned,
        author_id=staff_user.id,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post, attribute_names=["author", "replies"])
    return _post_to_detail(post)


@router.get("/{post_id}", response_model=PostDetailResponse)
async def get_post(
    post_id: int,
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> PostDetailResponse:
    """Get a single post with all its replies."""
    query = (
        select(BoardPost)
        .options(
            selectinload(BoardPost.author),
            selectinload(BoardPost.replies).selectinload(BoardReply.author),
        )
        .where(BoardPost.id == post_id)
    )
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _post_to_detail(post)


@router.put("/{post_id}", response_model=PostDetailResponse)
async def update_post(
    post_id: int,
    post_in: PostUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> PostDetailResponse:
    """Update a post. Only the author or admins can update."""
    query = (
        select(BoardPost)
        .options(
            selectinload(BoardPost.author),
            selectinload(BoardPost.replies).selectinload(BoardReply.author),
        )
        .where(BoardPost.id == post_id)
    )
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Only author or admin can edit
    is_admin = staff_user.role in ("ADMIN", "SUPER_ADMIN")
    if post.author_id != staff_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only edit your own posts")

    update_data = post_in.model_dump(exclude_unset=True)

    # Validate category if provided
    if "category" in update_data:
        valid_categories = [c.value for c in MessageBoardCategory]
        if update_data["category"] not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}",
            )

    # Only admins can pin/unpin
    if "pinned" in update_data and not is_admin:
        del update_data["pinned"]

    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post)
    return _post_to_detail(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a post. Only the author or admins can delete."""
    query = select(BoardPost).where(BoardPost.id == post_id)
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    is_admin = staff_user.role in ("ADMIN", "SUPER_ADMIN")
    if post.author_id != staff_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")

    await db.delete(post)
    await db.commit()


# ============================================================================
# Reply Endpoints
# ============================================================================


@router.post("/{post_id}/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
async def create_reply(
    post_id: int,
    reply_in: ReplyCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ReplyResponse:
    """Add a reply to a post."""
    # Verify post exists
    post_query = select(BoardPost).where(BoardPost.id == post_id)
    post_result = await db.execute(post_query)
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    reply = BoardReply(
        content=reply_in.content,
        post_id=post_id,
        author_id=staff_user.id,
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply, attribute_names=["author"])
    return ReplyResponse(
        id=reply.id,
        content=reply.content,
        author=AuthorResponse(id=reply.author.id, full_name=reply.author.full_name) if reply.author else None,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
    )


@router.put("/{post_id}/replies/{reply_id}", response_model=ReplyResponse)
async def update_reply(
    post_id: int,
    reply_id: int,
    reply_in: ReplyUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ReplyResponse:
    """Update a reply. Only the author or admins can update."""
    query = (
        select(BoardReply)
        .options(selectinload(BoardReply.author))
        .where(BoardReply.id == reply_id, BoardReply.post_id == post_id)
    )
    result = await db.execute(query)
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    is_admin = staff_user.role in ("ADMIN", "SUPER_ADMIN")
    if reply.author_id != staff_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only edit your own replies")

    reply.content = reply_in.content
    await db.commit()
    await db.refresh(reply)
    return ReplyResponse(
        id=reply.id,
        content=reply.content,
        author=AuthorResponse(id=reply.author.id, full_name=reply.author.full_name) if reply.author else None,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
    )


@router.delete("/{post_id}/replies/{reply_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reply(
    post_id: int,
    reply_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a reply. Only the author or admins can delete."""
    query = select(BoardReply).where(BoardReply.id == reply_id, BoardReply.post_id == post_id)
    result = await db.execute(query)
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    is_admin = staff_user.role in ("ADMIN", "SUPER_ADMIN")
    if reply.author_id != staff_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only delete your own replies")

    await db.delete(reply)
    await db.commit()
