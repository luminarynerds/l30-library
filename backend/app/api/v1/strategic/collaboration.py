# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strategic planning - Comments, notifications, and sharing endpoints."""

from typing import List, Optional
from functools import lru_cache
import hashlib

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cached, make_cache_key, set_cached
from app.core.database import get_db
from app.models.user import User
from app.schemas.strategic import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    CommentUserInfo,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services import strategic_service as svc
from ..auth import get_current_user, get_current_user_optional
from ..dependencies import is_admin
from .common import require_staff, require_admin

router = APIRouter(prefix="/strategic", tags=["strategic-collaboration"])


# ============ Comment Endpoints ============


def _user_info(user) -> Optional[CommentUserInfo]:
    if not user:
        return None
    return CommentUserInfo(
        id=user.id, email=user.email, name=getattr(user, "name", None)
    )


def _comment_response(comment, replies=None) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        goal_id=comment.goal_id,
        user_id=comment.user_id,
        content=comment.content,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        user=_user_info(comment.user) if hasattr(comment, "user") else None,
        replies=replies or [],
    )


@router.post("/goals/{goal_id}/comments", response_model=CommentResponse)
async def create_comment(
    goal_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a comment on a goal (authenticated users)."""
    comment = await svc.create_comment(
        goal_id, current_user.id, comment_data.content, comment_data.parent_id, db
    )
    return CommentResponse(
        id=comment.id,
        goal_id=comment.goal_id,
        user_id=comment.user_id,
        content=comment.content,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        user=CommentUserInfo(
            id=current_user.id,
            email=current_user.email,
            name=getattr(current_user, "name", None),
        ),
        replies=[],
    )


@router.get("/goals/{goal_id}/comments", response_model=List[CommentResponse])
async def list_comments(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List comments for a goal with nested replies."""
    raw_comments = await svc.list_comments(goal_id, db)
    return [
        CommentResponse(
            id=c["id"],
            goal_id=c["goal_id"],
            user_id=c["user_id"],
            content=c["content"],
            parent_id=c["parent_id"],
            created_at=c["created_at"],
            updated_at=c["updated_at"],
            user=_user_info(c["user"]),
            replies=[
                CommentResponse(
                    id=r["id"],
                    goal_id=r["goal_id"],
                    user_id=r["user_id"],
                    content=r["content"],
                    parent_id=r["parent_id"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    user=_user_info(r["user"]),
                    replies=[],
                )
                for r in c.get("replies", [])
            ],
        )
        for c in raw_comments
    ]


@router.get("/comments/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific comment with replies."""
    comment, replies = await svc.get_comment_by_id(comment_id, db)
    return CommentResponse(
        id=comment.id,
        goal_id=comment.goal_id,
        user_id=comment.user_id,
        content=comment.content,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        user=_user_info(comment.user) if hasattr(comment, "user") else None,
        replies=[_comment_response(r) for r in replies],
    )


@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a comment (owner only)."""
    comment = await svc.update_comment(
        comment_id, comment_data.content, current_user.id, db
    )
    return _comment_response(comment)


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a comment (owner or admin)."""
    user_is_admin = is_admin(current_user)
    await svc.delete_comment(comment_id, current_user.id, user_is_admin, db)
    return {"message": "Comment deleted"}


# ============ Notification Endpoints ============


@router.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's notifications."""
    notifications = await svc.list_notifications(
        current_user.id, db, page=page, per_page=per_page, unread_only=unread_only
    )
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    await svc.mark_notification_read(notification_id, current_user.id, db)
    return {"message": "Notification marked as read"}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all user's notifications as read."""
    count = await svc.mark_all_notifications_read(current_user.id, db)
    return {"message": f"Marked {count} notifications as read", "count": count}


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get count of unread notifications.

    Uses composite index on (user_id, is_read) for fast queries.
    Result is cached for 10 seconds to reduce database load.
    """
    cache_key = make_cache_key("notifications:unread-count", user_id=current_user.id)
    cached_result = await get_cached(cache_key)
    if cached_result is not None:
        return UnreadCountResponse(**cached_result)

    count = await svc.get_unread_notification_count(current_user.id, db)
    response = UnreadCountResponse(unread_count=count)
    await set_cached(cache_key, response.model_dump(), ttl_seconds=10)
    return response
