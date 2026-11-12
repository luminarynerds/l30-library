# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lists and badges sub-router for school reading partnerships.

Extracted from the former ``school_reading_partnerships.py`` monolith.
The full import surface from that file is preserved here so behavior of
moved routes is byte-for-byte identical; unused imports in this slice are
intentional and may be pruned in a follow-up.
"""

from app.core.logging import get_logger
from datetime import datetime, timezone

logger = get_logger(__name__)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.rate_limit import limiter
from ....models.outreach import OutreachPartner, BulkCheckout, PartnershipTier, OutreachPartnerStatus
from ....models.reading import (
    ReadingLogEntry,
    ReadingProgram,
    ReadingRegistration,
    SchoolBadge,
    SchoolBadgeEarned,
    SharedReadingList,
    SharedReadingListItem,
    FamilyReadingChallenge,
    FamilyChallengeRegistration,
    TakeHomeReadingBundle,
    BundleDistribution,
    TeacherTrainingModule,
    TrainingCompletion,
    LibraryVisitRequest,
    ReadingListRequest,
    ReadingAmbassadorCertification,
    LibrarianConsultationSlot,
    ConsultationAttendee,
)
from ....models.user import User, UserRole
from ....schemas.reading import (
    SchoolBadgeCreate,
    SchoolBadgeResponse,
    SharedReadingListCreate,
    SharedReadingListItemCreate,
    SharedReadingListItemResponse,
    SharedReadingListResponse,
    FamilyReadingChallengeCreate,
    FamilyReadingChallengeResponse,
    FamilyChallengeRegistrationCreate,
    FamilyChallengeRegistrationResponse,
    TakeHomeReadingBundleCreate,
    TakeHomeReadingBundleResponse,
    TeacherTrainingModuleCreate,
    TeacherTrainingModuleResponse,
    TrainingCompletionResponse,
    ReadingAmbassadorCertificationCreate,
    ReadingAmbassadorCertificationResponse,
    ReadingAmbassadorCertificationListResponse,
    ReadingAmbassadorCertificationListItem,
    ReadingAmbassadorCertificationUpdate,
    LibrarianConsultationSlotCreate,
    LibrarianConsultationSlotResponse,
    LibraryVisitRequestCreate,
    LibraryVisitRequestResponse,
    LibraryVisitApprove,
    LibraryVisitReject,
    ReadingListRequestCreate,
    ReadingListRequestResponse,
    ReadingListRequestReject,
)
from ..auth import get_current_user
from ..dependencies import check_staff_access
from ..feature_guards import require_for_teachers_enabled
from ._shared import (
    require_teacher_or_staff,
    require_teacher_of_school,
    assert_teacher_access_to_school,
    _strip_patron_identifiers,
    _PATRON_ID_FIELDS,
)

router = APIRouter()


# ============================================================================
# Shared Reading Lists - for librarian/teacher collaboration
# ============================================================================


@router.post(
    "/schools/{school_id}/reading-lists", response_model=SharedReadingListResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("60/minute")
async def create_shared_reading_list(
    request: Request,
    school_id: int,
    list_data: SharedReadingListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a shared reading list for a school. Staff only."""
    check_staff_access(current_user)

    # Verify school exists
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Create reading list
    reading_list = SharedReadingList(
        name=list_data.name,
        description=list_data.description,
        partner_id=school_id,
        program_id=list_data.program_id,
        curriculum_alignment=list_data.curriculum_alignment,
        grade_levels=list_data.grade_levels,
        reading_levels=list_data.reading_levels,
        topics=list_data.topics,
        is_active=list_data.is_active,
        created_by_id=current_user.id,
    )

    db.add(reading_list)
    await db.commit()
    await db.refresh(reading_list)

    return reading_list


@router.get(
    "/schools/{school_id}/reading-lists",
    response_model=List[SharedReadingListResponse],
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_school_reading_lists(
    request: Request,
    school_id: int,
    active_only: bool = Query(False),
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List all reading lists for a school."""
    # Verify school exists
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Fetch reading lists
    conditions = [SharedReadingList.partner_id == school_id]
    if active_only:
        conditions.append(SharedReadingList.is_active == True)

    query = (
        select(SharedReadingList)
        .where(*conditions)
        .options(selectinload(SharedReadingList.items))
        .order_by(SharedReadingList.created_at.desc())
    )

    result = await db.execute(query)
    reading_lists = result.scalars().unique().all()

    return reading_lists


@router.get(
    "/reading-lists/{list_id}",
    response_model=SharedReadingListResponse,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def get_reading_list(
    request: Request,
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific reading list with all items."""
    query = select(SharedReadingList).where(SharedReadingList.id == list_id).options(selectinload(SharedReadingList.items))

    result = await db.execute(query)
    reading_list = result.scalar_one_or_none()

    if not reading_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading list not found")

    assert_teacher_access_to_school(current_user, reading_list.partner_id)

    return reading_list


@router.post("/reading-lists/{list_id}/items", response_model=SharedReadingListItemResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def add_item_to_reading_list(
    request: Request,
    list_id: int,
    item_data: SharedReadingListItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a book item to a reading list. Staff or teacher."""
    require_teacher_or_staff(current_user)

    # Verify reading list exists
    reading_list = await get_or_404(db, SharedReadingList, list_id, "Reading list not found")
    assert_teacher_access_to_school(current_user, reading_list.partner_id)

    # Create list item
    list_item = SharedReadingListItem(
        reading_list_id=list_id,
        isbn=item_data.isbn,
        title=item_data.title,
        author=item_data.author,
        reading_level=item_data.reading_level,
        description=item_data.description,
        book_cover_url=item_data.book_cover_url,
        tags=item_data.tags,
        librarian_notes=item_data.librarian_notes,
        teacher_notes=item_data.teacher_notes,
        suggested_by_id=current_user.id,
    )

    db.add(list_item)
    await db.commit()
    await db.refresh(list_item)

    return list_item


@router.delete("/reading-lists/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def remove_item_from_reading_list(
    request: Request,
    list_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an item from a reading list. Staff only."""
    check_staff_access(current_user)

    # Verify list item exists
    item_result = await db.execute(
        select(SharedReadingListItem).where(
            and_(SharedReadingListItem.id == item_id, SharedReadingListItem.reading_list_id == list_id)
        )
    )
    list_item = item_result.scalar_one_or_none()
    if not list_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List item not found")

    await db.delete(list_item)
    await db.commit()


# ============================================================================
# School Badges - school-specific achievements
# ============================================================================


@router.post(
    "/schools/{school_id}/badges", response_model=SchoolBadgeResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("60/minute")
async def create_school_badge(
    request: Request,
    school_id: int,
    badge_data: SchoolBadgeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a school-specific badge. Staff only."""
    check_staff_access(current_user)

    # Verify school exists
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Create badge
    badge = SchoolBadge(
        partner_id=school_id,
        badge_name=badge_data.badge_name,
        badge_description=badge_data.badge_description,
        badge_icon_url=badge_data.badge_icon_url,
        threshold_type=badge_data.threshold_type,
        threshold_value=badge_data.threshold_value,
        is_active=badge_data.is_active,
    )

    db.add(badge)
    await db.commit()
    await db.refresh(badge)

    return badge


@router.get(
    "/schools/{school_id}/badges",
    response_model=List[SchoolBadgeResponse],
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_school_badges(
    request: Request,
    school_id: int,
    active_only: bool = Query(False),
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List all badges for a school."""
    # Verify school exists
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Fetch badges
    conditions = [SchoolBadge.partner_id == school_id]
    if active_only:
        conditions.append(SchoolBadge.is_active == True)

    query = select(SchoolBadge).where(*conditions).order_by(SchoolBadge.created_at.desc())

    result = await db.execute(query)
    badges = result.scalars().all()

    return badges


# ============================================================================
# Teacher Dashboard Data
# ============================================================================


class TeacherDashboardData(BaseModel):
    school_id: int
    school_name: str
    active_reading_programs: List[dict]
    student_registration_count: int
    recent_reading_activity: List[dict]
    class_progress_summary: dict
    school_badges_available: List[SchoolBadgeResponse]


@router.get(
    "/teacher-dashboard/{school_id}",
    response_model=dict,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def get_teacher_dashboard(
    request: Request,
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get teacher dashboard data for a school."""
    require_teacher_or_staff(current_user)

    # Teachers are scoped to their own school. Staff/admin/director see any school.
    if current_user.role == UserRole.TEACHER and current_user.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teachers can only view their assigned school",
        )

    # Get school
    school = await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Get reading programs for this school
    programs_result = await db.execute(
        select(ReadingProgram).where(
            and_(ReadingProgram.partner_id == school_id, ReadingProgram.is_active == True)
        )
    )
    programs = programs_result.scalars().all()

    # Count student registrations
    reg_count_result = await db.execute(
        select(func.count(ReadingRegistration.id)).where(ReadingRegistration.program_id.in_([p.id for p in programs]))
    )
    student_count = reg_count_result.scalar() or 0

    # Get recent reading activity
    activity_result = await db.execute(
        select(ReadingLogEntry)
        .join(ReadingRegistration)
        .where(ReadingRegistration.program_id.in_([p.id for p in programs]))
        .order_by(ReadingLogEntry.logged_at.desc())
        .limit(10)
    )
    recent_activity = activity_result.scalars().all()

    # Get school badges
    badges_result = await db.execute(select(SchoolBadge).where(SchoolBadge.partner_id == school_id))
    badges = badges_result.scalars().all()

    # Calculate class progress
    total_minutes = 0
    total_books = 0
    for log in recent_activity:
        total_minutes += log.minutes_read
        total_books += log.books_read

    dashboard = {
        "school_id": school_id,
        "school_name": school.name,
        "active_programs_count": len(programs),
        "student_registration_count": student_count,
        "total_reading_activity": len(recent_activity),
        "total_minutes_read": total_minutes,
        "total_books_read": total_books,
        "school_badges": badges,
        "recent_activity_count": len(recent_activity),
    }
    # Explicit isolation: strip any patron identifiers before returning
    return _strip_patron_identifiers(dashboard)


