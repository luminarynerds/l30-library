# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API endpoints for social sharing and share tracking."""

from typing import Optional
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.exceptions import InternalServerError
from ...core.error_codes import ErrorCode
from ...core.shortcuts import get_or_404
from ...models import (
    CatalogItem, Event, ReadingList, ShareEvent, ShareableResourceType,
    SharePlatform, ShareStatistics
)
from ...models.social_sharing import SocialSharingConfig
from ...models.user import User, UserRole
from .auth import get_current_user
from .dependencies import is_admin, require_staff


class SocialSharingConfigUpdate(BaseModel):
    sharing_enabled: bool = True
    share_buttons_enabled: bool = True
    share_counts_enabled: bool = True
    default_message_template: Optional[str] = None
    twitter_handle: Optional[str] = None
    facebook_app_id: Optional[str] = None
    linkedin_enabled: bool = True
    pinterest_enabled: bool = False
    email_enabled: bool = True
    copy_link_enabled: bool = True
    og_default_image: Optional[str] = None
    utm_tracking_enabled: bool = False
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None

logger = get_logger(__name__)

router = APIRouter(prefix="/sharing", tags=["sharing"])


def _config_to_dict(config: SocialSharingConfig) -> dict:
    return {
        "sharing_enabled": config.sharing_enabled,
        "share_buttons_enabled": config.share_buttons_enabled,
        "share_counts_enabled": config.share_counts_enabled,
        "default_message_template": config.default_message_template,
        "twitter_handle": config.twitter_handle,
        "facebook_app_id": config.facebook_app_id,
        "linkedin_enabled": config.linkedin_enabled,
        "pinterest_enabled": config.pinterest_enabled,
        "email_enabled": config.email_enabled,
        "copy_link_enabled": config.copy_link_enabled,
        "og_default_image": config.og_default_image,
        "utm_tracking_enabled": config.utm_tracking_enabled,
        "utm_source": config.utm_source,
        "utm_medium": config.utm_medium,
    }


_DEFAULT_CONFIG = {
    "sharing_enabled": True,
    "share_buttons_enabled": True,
    "share_counts_enabled": True,
    "default_message_template": None,
    "twitter_handle": None,
    "facebook_app_id": None,
    "linkedin_enabled": True,
    "pinterest_enabled": False,
    "email_enabled": True,
    "copy_link_enabled": True,
    "og_default_image": None,
    "utm_tracking_enabled": False,
    "utm_source": None,
    "utm_medium": None,
}


@router.get("/config")
async def get_sharing_config(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get the current social sharing configuration.

    This is a public endpoint so the share service can read UTM settings
    without requiring authentication.
    """
    config = (await db.execute(select(SocialSharingConfig))).scalars().first()
    if not config:
        return _DEFAULT_CONFIG
    return _config_to_dict(config)


@router.put("/config")
async def update_sharing_config(
    body: SocialSharingConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Update the social sharing configuration. Requires admin role.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    config = (await db.execute(select(SocialSharingConfig))).scalars().first()

    if not config:
        config = SocialSharingConfig(updated_by_id=current_user.id)
        db.add(config)

    # Apply all fields from the request body
    for field, value in body.model_dump().items():
        setattr(config, field, value)

    config.updated_by_id = current_user.id

    await db.flush()

    return _config_to_dict(config)


@router.post("/track")
async def track_share(
    resource_type: ShareableResourceType = Query(..., description="Type of resource being shared"),
    resource_id: int = Query(..., description="ID of the resource being shared"),
    platform: SharePlatform = Query(..., description="Platform being shared to"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Track a share event for analytics.

    - **resource_type**: Type of resource (book, event, reading_list, author_profile, staff_pick)
    - **resource_id**: ID of the resource being shared
    - **platform**: Platform shared to (facebook, twitter, linkedin, reddit, email, copy_link, etc.)
    """
    try:
        # Verify the resource exists and get public status
        is_public = True

        if resource_type == ShareableResourceType.book:
            item = await get_or_404(db, CatalogItem, resource_id, "Book not found")
            is_public = True  # Books are always public in library context

        elif resource_type == ShareableResourceType.event:
            event = await get_or_404(db, Event, resource_id, "Event not found")
            is_public = event.is_published

        elif resource_type == ShareableResourceType.reading_list:
            reading_list = await get_or_404(db, ReadingList, resource_id, "Reading list not found")
            is_public = reading_list.is_public

        else:
            # For other types, assume public
            is_public = True

        # Create share event record
        share_event = ShareEvent(
            user_id=current_user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            platform=platform,
            is_public_resource=is_public,
        )
        db.add(share_event)

        # Update or create share statistics
        stats = (await db.execute(select(ShareStatistics).where(
            ShareStatistics.resource_type == resource_type,
            ShareStatistics.resource_id == resource_id
        ))).scalars().first()

        if not stats:
            stats = ShareStatistics(
                resource_type=resource_type,
                resource_id=resource_id,
                total_shares=0,
                facebook_shares=0,
                twitter_shares=0,
                linkedin_shares=0,
                reddit_shares=0,
                email_shares=0,
                copy_link_shares=0,
                whatsapp_shares=0,
                telegram_shares=0,
            )
            db.add(stats)

        stats.total_shares += 1

        # Increment platform-specific counter
        if platform == SharePlatform.facebook:
            stats.facebook_shares += 1
        elif platform == SharePlatform.twitter:
            stats.twitter_shares += 1
        elif platform == SharePlatform.linkedin:
            stats.linkedin_shares += 1
        elif platform == SharePlatform.reddit:
            stats.reddit_shares += 1
        elif platform == SharePlatform.email:
            stats.email_shares += 1
        elif platform == SharePlatform.copy_link:
            stats.copy_link_shares += 1
        elif platform == SharePlatform.whatsapp:
            stats.whatsapp_shares += 1
        elif platform == SharePlatform.telegram:
            stats.telegram_shares += 1

        stats.last_shared_at = func.now()

        # Update share_count on the resource itself
        if resource_type == ShareableResourceType.book:
            item = (await db.execute(select(CatalogItem).where(CatalogItem.id == resource_id))).scalars().first()
            if item:
                item.share_count += 1

        elif resource_type == ShareableResourceType.event:
            event = (await db.execute(select(Event).where(Event.id == resource_id))).scalars().first()
            if event:
                event.share_count += 1

        elif resource_type == ShareableResourceType.reading_list:
            reading_list = (await db.execute(select(ReadingList).where(ReadingList.id == resource_id))).scalars().first()
            if reading_list:
                reading_list.share_count += 1

        await db.flush()

        return {
            "success": True,
            "message": f"Share tracked on {platform}",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "platform": platform,
        }

    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("Failed to track share event")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.get("/stats/{resource_type}/{resource_id}")
async def get_share_stats(
    resource_type: ShareableResourceType,
    resource_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get share statistics for a resource.

    - **resource_type**: Type of resource (book, event, reading_list, etc.)
    - **resource_id**: ID of the resource
    """
    stats = (await db.execute(select(ShareStatistics).where(
        ShareStatistics.resource_type == resource_type,
        ShareStatistics.resource_id == resource_id
    ))).scalars().first()

    if not stats:
        # Return default stats if none exist
        return {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "total_shares": 0,
            "facebook_shares": 0,
            "twitter_shares": 0,
            "linkedin_shares": 0,
            "reddit_shares": 0,
            "email_shares": 0,
            "copy_link_shares": 0,
            "whatsapp_shares": 0,
            "telegram_shares": 0,
            "last_shared_at": None,
        }

    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "total_shares": stats.total_shares,
        "facebook_shares": stats.facebook_shares,
        "twitter_shares": stats.twitter_shares,
        "linkedin_shares": stats.linkedin_shares,
        "reddit_shares": stats.reddit_shares,
        "email_shares": stats.email_shares,
        "copy_link_shares": stats.copy_link_shares,
        "whatsapp_shares": stats.whatsapp_shares,
        "telegram_shares": stats.telegram_shares,
        "last_shared_at": stats.last_shared_at.isoformat() if stats.last_shared_at else None,
    }


@router.get("/stats")
async def get_aggregate_share_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get aggregate share statistics for the admin dashboard.
    Requires authentication.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # Count share events by time window
    total_today = (await db.execute(
        select(func.count()).select_from(ShareEvent).where(
            ShareEvent.shared_at >= today_start
        )
    )).scalar() or 0

    total_week = (await db.execute(
        select(func.count()).select_from(ShareEvent).where(
            ShareEvent.shared_at >= week_start
        )
    )).scalar() or 0

    total_month = (await db.execute(
        select(func.count()).select_from(ShareEvent).where(
            ShareEvent.shared_at >= month_start
        )
    )).scalar() or 0

    # Platform breakdown from ShareStatistics aggregate
    all_stats = (await db.execute(select(ShareStatistics))).scalars().all()

    shares_by_platform = {
        "facebook": sum(s.facebook_shares for s in all_stats),
        "twitter": sum(s.twitter_shares for s in all_stats),
        "linkedin": sum(s.linkedin_shares for s in all_stats),
        "reddit": sum(s.reddit_shares for s in all_stats),
        "email": sum(s.email_shares for s in all_stats),
        "copy_link": sum(s.copy_link_shares for s in all_stats),
        "whatsapp": sum(s.whatsapp_shares for s in all_stats),
        "telegram": sum(s.telegram_shares for s in all_stats),
    }

    # Top shared items
    top_items_rows = (await db.execute(
        select(ShareStatistics)
        .order_by(ShareStatistics.total_shares.desc())
        .limit(10)
    )).scalars().all()

    most_shared_items = []
    for row in top_items_rows:
        if row.total_shares <= 0:
            continue
        # Try to get item title
        item_title = f"{row.resource_type} #{row.resource_id}"
        if row.resource_type == ShareableResourceType.book:
            item = (await db.execute(
                select(CatalogItem).where(CatalogItem.id == row.resource_id)
            )).scalars().first()
            if item:
                item_title = item.title
        elif row.resource_type == ShareableResourceType.event:
            event = (await db.execute(
                select(Event).where(Event.id == row.resource_id)
            )).scalars().first()
            if event:
                item_title = event.title
        elif row.resource_type == ShareableResourceType.reading_list:
            rl = (await db.execute(
                select(ReadingList).where(ReadingList.id == row.resource_id)
            )).scalars().first()
            if rl:
                item_title = rl.name
        most_shared_items.append({
            "item_id": row.resource_id,
            "item_title": item_title,
            "share_count": row.total_shares,
        })

    return {
        "total_shares_today": total_today,
        "total_shares_week": total_week,
        "total_shares_month": total_month,
        "shares_by_platform": shares_by_platform,
        "most_shared_items": most_shared_items,
    }


@router.get("/analytics/top-shared")
async def get_top_shared_resources(
    resource_type: Optional[ShareableResourceType] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """
    Get the most shared resources.

    - **resource_type**: Filter by resource type (optional)
    - **limit**: Maximum number of results (default: 10, max: 100)
    """
    stmt = select(ShareStatistics).order_by(ShareStatistics.total_shares.desc())

    if resource_type:
        stmt = stmt.where(ShareStatistics.resource_type == resource_type)

    stats = (await db.execute(stmt.limit(limit))).scalars().all()

    return {
        "count": len(stats),
        "resources": [
            {
                "resource_type": s.resource_type,
                "resource_id": s.resource_id,
                "total_shares": s.total_shares,
                "last_shared_at": s.last_shared_at.isoformat() if s.last_shared_at else None,
            }
            for s in stats
        ],
    }


@router.get("/analytics/platform-breakdown")
async def get_platform_breakdown(
    resource_type: Optional[ShareableResourceType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """
    Get breakdown of shares by platform.

    - **resource_type**: Filter by resource type (optional)
    """
    stmt = select(ShareStatistics)

    if resource_type:
        stmt = stmt.where(ShareStatistics.resource_type == resource_type)

    stats = (await db.execute(stmt)).scalars().all()

    breakdown = {
        "facebook": sum(s.facebook_shares for s in stats),
        "twitter": sum(s.twitter_shares for s in stats),
        "linkedin": sum(s.linkedin_shares for s in stats),
        "reddit": sum(s.reddit_shares for s in stats),
        "email": sum(s.email_shares for s in stats),
        "copy_link": sum(s.copy_link_shares for s in stats),
        "whatsapp": sum(s.whatsapp_shares for s in stats),
        "telegram": sum(s.telegram_shares for s in stats),
    }

    total = sum(breakdown.values())

    return {
        "total_shares": total,
        "by_platform": breakdown,
        "percentages": {
            k: round((v / total * 100) if total > 0 else 0, 2) for k, v in breakdown.items()
        },
    }


@router.get("/user/share-history")
async def get_user_share_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get the current user's share history.

    - **limit**: Number of records to return (default: 50)
    - **offset**: Number of records to skip for pagination (default: 0)
    """
    total_count = (await db.execute(
        select(func.count()).select_from(ShareEvent).where(ShareEvent.user_id == current_user.id)
    )).scalar()

    shares = (await db.execute(
        select(ShareEvent)
        .where(ShareEvent.user_id == current_user.id)
        .order_by(ShareEvent.shared_at.desc())
        .offset(offset)
        .limit(limit)
    )).scalars().all()

    return {
        "total_count": total_count,
        "offset": offset,
        "limit": limit,
        "shares": [
            {
                "id": s.id,
                "resource_type": s.resource_type,
                "resource_id": s.resource_id,
                "platform": s.platform,
                "is_public_resource": s.is_public_resource,
                "shared_at": s.shared_at.isoformat() if s.shared_at else None,
            }
            for s in shares
        ],
    }
