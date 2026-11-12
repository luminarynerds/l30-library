# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Announcements API - Library-wide notifications for patrons"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, cast, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.pagination import PaginationParams, calculate_total_pages
from ...schemas.common import PaginatedResponse, PaginationInfo
from ...models.announcements import Announcement, AnnouncementPriority, AnnouncementStatus
from ...models.user import User
from .auth import get_current_user, get_optional_user
from .dependencies import check_staff_access, check_admin_access

router = APIRouter(prefix="/announcements", tags=["announcements"])


# ============================================================================
# Schemas
# ============================================================================


class AnnouncementResponse(BaseModel):

    id: int
    title: str
    content: str
    summary: Optional[str] = None
    category: str = "general"
    priority: AnnouncementPriority
    status: AnnouncementStatus
    active: bool
    pinned: bool = False
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    show_on_homepage: bool
    show_banner: bool
    dismissible: bool
    target_audience: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_name: Optional[str] = None
    # Alias for frontend compatibility
    author_name: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, announcement: Announcement) -> "AnnouncementResponse":
        return cls(
            id=announcement.id,
            title=announcement.title,
            content=announcement.content,
            summary=announcement.summary,
            category=announcement.category or "general",
            priority=announcement.priority,
            status=announcement.status or AnnouncementStatus.DRAFT,
            active=announcement.active,
            pinned=announcement.pinned or False,
            starts_at=announcement.starts_at,
            ends_at=announcement.ends_at,
            expires_at=announcement.expires_at,
            published_at=announcement.published_at,
            show_on_homepage=announcement.show_on_homepage,
            show_banner=announcement.show_banner,
            dismissible=announcement.dismissible,
            target_audience=announcement.target_audience,
            created_at=announcement.created_at,
            updated_at=announcement.updated_at,
            created_by_name=announcement.created_by_name,
            author_name=announcement.created_by_name,
        )


class AnnouncementCreate(BaseModel):

    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    summary: Optional[str] = Field(default=None, max_length=500)
    category: str = Field(default="general", max_length=50)
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    expires_at: Optional[str] = None
    pinned: bool = False
    show_on_homepage: bool = True
    show_banner: bool = False
    dismissible: bool = True
    target_audience: Optional[str] = Field(default=None, max_length=50)


class AnnouncementUpdate(BaseModel):

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1)
    summary: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=50)
    priority: Optional[AnnouncementPriority] = None
    status: Optional[AnnouncementStatus] = None
    expires_at: Optional[str] = None
    pinned: Optional[bool] = None
    show_on_homepage: Optional[bool] = None
    show_banner: Optional[bool] = None
    dismissible: Optional[bool] = None
    target_audience: Optional[str] = Field(default=None, max_length=50)


# ============================================================================
# Helper Functions
# ============================================================================




# ============================================================================
# Public Endpoints
# ============================================================================


@router.get("", response_model=PaginatedResponse[AnnouncementResponse])
async def list_announcements(
    active_only: bool = Query(
        default=True, description="Only return currently active announcements"
    ),
    priority: Optional[AnnouncementPriority] = Query(
        default=None, description="Filter by priority"
    ),
    target_audience: Optional[str] = Query(
        default=None, description="Filter by target audience"
    ),
    homepage_only: bool = Query(
        default=False, description="Only return homepage announcements"
    ),
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="Filter by status (draft, published, archived)"
    ),
    category: Optional[str] = Query(
        default=None, description="Filter by category"
    ),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> PaginatedResponse[AnnouncementResponse]:
    """
    List announcements.

    - **active_only**: Only show currently active announcements (default: true)
    - **priority**: Filter by priority (low, normal, high, urgent)
    - **status**: Filter by status (draft, published, archived)
    - **category**: Filter by category
    - **target_audience**: Filter by target audience (all, staff, patrons, students)
    - **homepage_only**: Only show announcements marked for homepage
    """
    query = select(Announcement)
    count_query = select(func.count(Announcement.id))

    # Filter by status
    if status_filter:
        try:
            status_enum = AnnouncementStatus(status_filter)
            query = query.where(Announcement.status == status_enum)
            count_query = count_query.where(Announcement.status == status_enum)
        except ValueError:
            pass

    # Filter by active status and dates
    if active_only:
        now = datetime.now(timezone.utc)

        # When filtering by status, skip the active boolean check (status
        # already narrows the set), but still apply date/expiration filters
        # so stale announcements don't leak through.
        if not status_filter:
            query = query.where(Announcement.active == True)
            count_query = count_query.where(Announcement.active == True)

        # Filter by start/end dates
        date_filters = [
            or_(Announcement.starts_at == None, Announcement.starts_at <= now),
            or_(Announcement.ends_at == None, Announcement.ends_at > now),
            or_(Announcement.expires_at == None, Announcement.expires_at > now),
        ]
        query = query.where(*date_filters)
        count_query = count_query.where(*date_filters)

    # Filter by category
    if category:
        query = query.where(Announcement.category == category)
        count_query = count_query.where(Announcement.category == category)

    # Filter by priority
    if priority:
        query = query.where(Announcement.priority == priority)
        count_query = count_query.where(Announcement.priority == priority)

    # Filter by target audience
    if target_audience:
        audience_filter = or_(
            Announcement.target_audience == None,
            Announcement.target_audience == target_audience,
            Announcement.target_audience == "all",
        )
        query = query.where(audience_filter)
        count_query = count_query.where(audience_filter)

    # Auto-filter: hide staff-only announcements from non-staff users
    is_staff = current_user and current_user.role in ("STAFF", "ADMIN", "SUPER_ADMIN")
    if not is_staff:
        public_filter = or_(
            Announcement.target_audience == None,
            Announcement.target_audience == "",
            Announcement.target_audience == "all",
            Announcement.target_audience == "patrons",
        )
        query = query.where(public_filter)
        count_query = count_query.where(public_filter)

    # Filter by homepage
    if homepage_only:
        query = query.where(Announcement.show_on_homepage == True)
        count_query = count_query.where(Announcement.show_on_homepage == True)

    # Count query
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order: pinned first, then by priority (urgent first), then created date
    priority_rank = case(
        (cast(Announcement.priority, String) == 'urgent', 0),
        (cast(Announcement.priority, String) == 'high', 1),
        (cast(Announcement.priority, String) == 'important', 1),
        (cast(Announcement.priority, String) == 'normal', 2),
        (cast(Announcement.priority, String) == 'low', 3),
        else_=4,
    )

    query = (
        query.order_by(
            Announcement.pinned.desc(),
            priority_rank.asc(),
            Announcement.created_at.desc(),
        )
        .offset(pagination.offset)
        .limit(pagination.limit)
    )

    result = await db.execute(query)
    items = result.scalars().all()

    total_pages = calculate_total_pages(total, pagination.page_size)
    return PaginatedResponse(
        data=[AnnouncementResponse.from_model(a) for a in items],
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: int, db: AsyncSession = Depends(get_db)
) -> AnnouncementResponse:
    """Get a single announcement by ID"""
    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
        )

    return AnnouncementResponse.from_model(announcement)


# ============================================================================
# Staff/Admin Endpoints (same base path, auth-protected)
# ============================================================================


@router.post(
    "",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnouncementResponse:
    """
    Create a new announcement (staff/admin only).

    Announcements start as drafts. Use PATCH to publish.
    """
    check_staff_access(current_user)

    data = announcement_data.model_dump(exclude={"expires_at"})

    # Parse expires_at date string
    if announcement_data.expires_at:
        try:
            data["expires_at"] = datetime.fromisoformat(
                announcement_data.expires_at + "T23:59:59+00:00"
                if "T" not in announcement_data.expires_at
                else announcement_data.expires_at
            )
        except (ValueError, TypeError):
            data["expires_at"] = None

    announcement = Announcement(
        **data,
        status=AnnouncementStatus.DRAFT,
        active=True,
        created_by_id=current_user.id,
        created_by_name=f"{current_user.first_name} {current_user.last_name}",
    )

    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)

    return AnnouncementResponse.from_model(announcement)


@router.put("/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: int,
    update_data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnouncementResponse:
    """Update an announcement (staff/admin only)"""
    check_staff_access(current_user)

    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)

    # Parse expires_at date string
    if "expires_at" in update_dict and update_dict["expires_at"]:
        try:
            update_dict["expires_at"] = datetime.fromisoformat(
                update_dict["expires_at"] + "T23:59:59+00:00"
                if "T" not in update_dict["expires_at"]
                else update_dict["expires_at"]
            )
        except (ValueError, TypeError):
            update_dict["expires_at"] = None

    for field, value in update_dict.items():
        setattr(announcement, field, value)

    await db.commit()
    await db.refresh(announcement)

    return AnnouncementResponse.from_model(announcement)


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an announcement (staff/admin only)"""
    check_staff_access(current_user)

    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
        )

    await db.delete(announcement)
    await db.commit()


@router.patch("/{announcement_id}", response_model=AnnouncementResponse)
async def patch_announcement(
    announcement_id: int,
    update_data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnouncementResponse:
    """
    Patch announcement fields (staff/admin only).

    Used for publish/archive status transitions:
    - { "status": "published" } to publish a draft
    - { "status": "archived" } to archive a published announcement
    """
    check_staff_access(current_user)

    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
        )

    update_dict = update_data.model_dump(exclude_unset=True)

    # Handle status transitions
    if "status" in update_dict:
        new_status = update_dict["status"]
        if new_status == AnnouncementStatus.PUBLISHED and announcement.status != AnnouncementStatus.PUBLISHED:
            update_dict["published_at"] = datetime.now(timezone.utc)
            update_dict["active"] = True

    for field, value in update_dict.items():
        setattr(announcement, field, value)

    await db.commit()
    await db.refresh(announcement)

    return AnnouncementResponse.from_model(announcement)


# ============================================================================
# Legacy Admin Endpoints (kept for backward compatibility)
# ============================================================================


@router.patch(
    "/admin/announcements/{announcement_id}/toggle", response_model=AnnouncementResponse
)
async def toggle_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnouncementResponse:
    """Toggle announcement active status (admin only)"""
    check_admin_access(current_user)

    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
        )

    announcement.active = not announcement.active

    await db.commit()
    await db.refresh(announcement)

    return AnnouncementResponse.from_model(announcement)


@router.get("/admin/announcements/stats/summary")
async def get_announcement_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    """Get announcement statistics (admin only)"""
    check_admin_access(current_user)

    now = datetime.now(timezone.utc)

    # Single SQL query instead of loading all announcements into memory
    stats_row = (await db.execute(
        select(
            func.count(Announcement.id).label("total"),
            func.count(Announcement.id).filter(
                and_(
                    Announcement.active == True,
                    or_(Announcement.starts_at.is_(None), Announcement.starts_at <= now),
                    or_(Announcement.ends_at.is_(None), Announcement.ends_at > now),
                )
            ).label("active_now"),
            func.count(Announcement.id).filter(
                and_(Announcement.starts_at.isnot(None), Announcement.starts_at > now)
            ).label("scheduled_future"),
        )
    )).one()

    # Priority breakdown via SQL
    priority_rows = (await db.execute(
        select(Announcement.priority, func.count(Announcement.id))
        .group_by(Announcement.priority)
    )).all()
    by_priority = {p.value: 0 for p in AnnouncementPriority}
    for row in priority_rows:
        if row[0]:
            by_priority[row[0].value] = row[1]

    # Status breakdown via SQL
    status_rows = (await db.execute(
        select(Announcement.status, func.count(Announcement.id))
        .group_by(Announcement.status)
    )).all()
    by_status = {s.value: 0 for s in AnnouncementStatus}
    for row in status_rows:
        if row[0]:
            by_status[row[0].value] = row[1]

    return {
        "total": stats_row.total,
        "total_announcements": stats_row.total,
        "active_now": stats_row.active_now,
        "scheduled_future": stats_row.scheduled_future,
        "published": by_status.get("published", 0),
        "draft": by_status.get("draft", 0),
        "archived": by_status.get("archived", 0),
        "by_priority": by_priority,
        "by_category": {},
    }
