# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Programs and reports sub-router for school reading partnerships.

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
    assert_teacher_access_to_school,
    require_teacher_of_school,
    require_teacher_or_staff,
    _strip_patron_identifiers,
    _PATRON_ID_FIELDS,
)

router = APIRouter()


# ============================================================================
# School Programs Management
# ============================================================================


@router.post("/schools/{school_id}/programs", status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_school_reading_program(
    request: Request,
    school_id: int,
    program_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a reading program for a school. Staff only."""
    check_staff_access(current_user)

    # Verify school exists
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Create reading program tied to school
    program = ReadingProgram(
        name=program_data.get("name"),
        description=program_data.get("description"),
        program_type=program_data.get("program_type", "special"),
        start_date=program_data.get("start_date"),
        end_date=program_data.get("end_date"),
        reading_goal_type=program_data.get("reading_goal_type"),
        reading_goal_value=program_data.get("reading_goal_value"),
        is_active=program_data.get("is_active", True),
        is_school_program=True,
        partner_id=school_id,
        curriculum_alignment=program_data.get("curriculum_alignment"),
        grade_levels=program_data.get("grade_levels", []),
        reading_levels=program_data.get("reading_levels", []),
        created_by_id=current_user.id,
    )

    db.add(program)
    await db.commit()
    await db.refresh(program)

    return program


@router.get(
    "/schools/{school_id}/programs",
    response_model=List[dict],
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_school_programs(
    request: Request,
    school_id: int,
    active_only: bool = Query(False),
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List all reading programs for a school."""
    # Verify school exists
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Fetch programs
    conditions = [ReadingProgram.partner_id == school_id]
    if active_only:
        conditions.append(ReadingProgram.is_active == True)

    query = select(ReadingProgram).where(*conditions).order_by(ReadingProgram.created_at.desc())

    result = await db.execute(query)
    programs = result.scalars().all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "program_type": p.program_type,
            "curriculum_alignment": p.curriculum_alignment,
            "grade_levels": p.grade_levels,
            "reading_levels": p.reading_levels,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "is_active": p.is_active,
        }
        for p in programs
    ]


# ============================================================================
# Enhanced Reporting - School-Program Correlation
# ============================================================================


@router.get("/reports/school-program-impact/{school_id}", response_model=dict)
@limiter.limit("60/minute")
async def get_school_program_impact_report(
    request: Request,
    school_id: int,
    start_date: str = Query("2024-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2024-12-31", description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get school-program correlation and impact metrics. Staff only."""
    check_staff_access(current_user)

    # Verify school exists
    school = await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Get all programs for the school
    programs_result = await db.execute(
        select(ReadingProgram).where(ReadingProgram.partner_id == school_id)
    )
    programs = programs_result.scalars().all()
    program_ids = [p.id for p in programs]

    if not program_ids:
        return {
            "school_id": school_id,
            "school_name": school.name,
            "period": f"{start_date} to {end_date}",
            "programs": [],
            "aggregate_metrics": {
                "total_students": 0,
                "total_minutes_read": 0,
                "total_books_read": 0,
                "average_minutes_per_student": 0,
                "programs_with_high_engagement": 0,
            },
            "recommendations": ["Create reading programs to engage students"],
        }

    # Get registrations for all programs
    registrations_result = await db.execute(
        select(func.count(ReadingRegistration.id).label("count"), ReadingRegistration.program_id)
        .where(ReadingRegistration.program_id.in_(program_ids))
        .group_by(ReadingRegistration.program_id)
    )
    registration_counts = {row[1]: row[0] for row in registrations_result.all()}

    # Get reading activity for all programs
    activity_result = await db.execute(
        select(
            func.sum(ReadingLogEntry.minutes_read).label("total_minutes"),
            func.sum(ReadingLogEntry.books_read).label("total_books"),
            ReadingLogEntry.registration_id,
        )
        .join(ReadingRegistration)
        .where(ReadingRegistration.program_id.in_(program_ids))
        .group_by(ReadingLogEntry.registration_id)
    )
    activities = activity_result.all()

    total_minutes = sum((a[0] or 0) for a in activities)
    total_books = sum((a[1] or 0) for a in activities)
    total_students = sum(registration_counts.values())

    # Build program details
    program_details = []
    high_engagement_count = 0

    for program in programs:
        prog_reg_count = registration_counts.get(program.id, 0)
        prog_activities = [a for a in activities if a[0] or a[1]]  # Filter non-zero activities
        prog_minutes = sum((a[0] or 0) for a in prog_activities)
        prog_books = sum((a[1] or 0) for a in prog_activities)

        engagement_rate = (prog_reg_count / total_students * 100) if total_students > 0 else 0
        if engagement_rate > 50:
            high_engagement_count += 1

        program_details.append(
            {
                "program_id": program.id,
                "program_name": program.name,
                "registrations": prog_reg_count,
                "total_minutes_read": prog_minutes,
                "total_books_read": prog_books,
                "engagement_rate": round(engagement_rate, 1),
                "curriculum_alignment": program.curriculum_alignment,
                "grade_levels": program.grade_levels,
            }
        )

    average_minutes_per_student = (total_minutes / total_students) if total_students > 0 else 0

    # Generate recommendations
    recommendations = []
    if high_engagement_count == 0:
        recommendations.append("Launch targeted campaigns to increase program awareness")
    elif high_engagement_count < len(programs) / 2:
        recommendations.append("Focus on underperforming programs to boost participation")
    else:
        recommendations.append("Excellent program engagement! Consider expanding successful models")

    if total_minutes < total_students * 100:  # Arbitrary threshold
        recommendations.append("Consider adding incentives to encourage more reading")

    return {
        "school_id": school_id,
        "school_name": school.name,
        "period": f"{start_date} to {end_date}",
        "programs": program_details,
        "aggregate_metrics": {
            "total_students": total_students,
            "total_minutes_read": total_minutes,
            "total_books_read": total_books,
            "average_minutes_per_student": round(average_minutes_per_student, 1),
            "programs_with_high_engagement": high_engagement_count,
        },
        "recommendations": recommendations,
    }


@router.get("/reports/school-comparison", response_model=dict)
@limiter.limit("60/minute")
async def get_school_comparison_report(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare reading program engagement across all schools. Staff only."""
    check_staff_access(current_user)

    # Get all schools
    schools_result = await db.execute(
        select(OutreachPartner).where(OutreachPartner.partner_type == "school")
    )
    schools = schools_result.scalars().all()

    school_stats = []

    for school in schools:
        # Get programs for this school
        programs_result = await db.execute(
            select(ReadingProgram).where(ReadingProgram.partner_id == school.id)
        )
        programs = programs_result.scalars().all()

        if not programs:
            continue

        program_ids = [p.id for p in programs]

        # Count registrations
        reg_count_result = await db.execute(
            select(func.count(ReadingRegistration.id)).where(
                ReadingRegistration.program_id.in_(program_ids)
            )
        )
        reg_count = reg_count_result.scalar() or 0

        # Sum activity
        activity_result = await db.execute(
            select(
                func.sum(ReadingLogEntry.minutes_read).label("minutes"),
                func.sum(ReadingLogEntry.books_read).label("books"),
            )
            .join(ReadingRegistration)
            .where(ReadingRegistration.program_id.in_(program_ids))
        )
        activity = activity_result.one()
        total_minutes = activity[0] or 0
        total_books = activity[1] or 0

        school_stats.append(
            {
                "school_id": school.id,
                "school_name": school.name,
                "program_count": len(programs),
                "student_registrations": reg_count,
                "total_minutes": total_minutes,
                "total_books": total_books,
                "average_minutes_per_student": (total_minutes / reg_count) if reg_count > 0 else 0,
            }
        )

    # Sort by engagement
    school_stats.sort(key=lambda x: x["total_minutes"], reverse=True)

    return {
        "total_schools": len(school_stats),
        "schools": school_stats,
        "insights": {
            "top_school": school_stats[0] if school_stats else None,
            "average_minutes_across_schools": round(
                sum(s["total_minutes"] for s in school_stats) / len(school_stats), 1
            )
            if school_stats
            else 0,
        },
    }


# ============================================================================
# Teacher Bulk Checkout Requests - Tied to Reading Programs
# ============================================================================


@router.post("/schools/{school_id}/bulk-checkout-request", status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_bulk_checkout_request_for_reading_program(
    request: Request,
    school_id: int,
    checkout_data: dict,
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a bulk checkout request tied to a reading program.
    Teachers can request collections of books for their class aligned with a reading program.
    """
    # Verify school exists
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # If reading program specified, verify it exists
    program_id = checkout_data.get("program_id")
    if program_id:
        program_result = await db.execute(
            select(ReadingProgram).where(ReadingProgram.id == program_id)
        )
        if not program_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading program not found")

    # Create bulk checkout request
    bulk_checkout = BulkCheckout(
        partner_id=school_id,
        checkout_name=checkout_data.get("checkout_name", "Reading Program Collection"),
        requestor_name=current_user.full_name or current_user.email,
        requestor_email=current_user.email,
        classroom_name=checkout_data.get("classroom_name"),
        grade_level=checkout_data.get("grade_level"),
        checkout_date=checkout_data.get("checkout_date"),
        due_date=checkout_data.get("due_date"),
        topic_requests=checkout_data.get("topic_requests", []),
        reading_level_min=checkout_data.get("reading_level_min"),
        reading_level_max=checkout_data.get("reading_level_max"),
        format_preferences=checkout_data.get("format_preferences", []),
        delivery_method=checkout_data.get("delivery_method", "pickup"),
        notes=f"Reading Program ID: {program_id}. {checkout_data.get('notes', '')}",
    )

    db.add(bulk_checkout)
    await db.commit()
    await db.refresh(bulk_checkout)

    return {
        "id": bulk_checkout.id,
        "checkout_name": bulk_checkout.checkout_name,
        "classroom_name": bulk_checkout.classroom_name,
        "checkout_date": bulk_checkout.checkout_date,
        "due_date": bulk_checkout.due_date,
        "status": bulk_checkout.status,
        "program_reference": program_id,
    }


@router.get("/schools/{school_id}/bulk-checkouts", response_model=List[dict])
@limiter.limit("120/minute")
async def list_school_bulk_checkouts(
    request: Request,
    school_id: int,
    status_filter: str = Query("all", description="Filter by status: all, active, returned"),
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List all bulk checkout requests for a school."""
    # Verify school exists
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Fetch bulk checkouts
    conditions = [BulkCheckout.partner_id == school_id]
    if status_filter != "all":
        conditions.append(BulkCheckout.status == status_filter)

    query = select(BulkCheckout).where(*conditions).order_by(BulkCheckout.checkout_date.desc())

    result = await db.execute(query)
    checkouts = result.scalars().all()

    # Explicit isolation: strip patron identifiers from bulk checkout list
    return _strip_patron_identifiers([
        {
            "id": c.id,
            "checkout_name": c.checkout_name,
            "classroom_name": c.classroom_name,
            "checkout_date": c.checkout_date,
            "due_date": c.due_date,
            "returned_date": c.returned_date,
            "status": c.status,
            "total_items": c.total_items,
            "items_returned": c.items_returned,
            "requestor_name": c.requestor_name,
        }
        for c in checkouts
    ])


@router.get("/bulk-checkout/{checkout_id}/program-recommendations", response_model=dict)
@limiter.limit("120/minute")
async def get_program_book_recommendations(
    request: Request,
    checkout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recommended books for a bulk checkout based on the linked reading program.
    Integrates reading program info with shared reading lists.
    """
    # Get the bulk checkout
    checkout = await get_or_404(db, BulkCheckout, checkout_id, "Bulk checkout not found")
    assert_teacher_access_to_school(current_user, checkout.partner_id)

    # Extract program ID from notes (if present)
    # In real implementation, you might want a foreign key relationship
    program_id = None
    if checkout.notes and "Reading Program ID:" in checkout.notes:
        try:
            program_id = int(checkout.notes.split("Reading Program ID: ")[1].split(".")[0])
        except (IndexError, ValueError) as e:
            logger.warning("Failed to extract program ID from checkout notes: %s", e)

    # Get shared reading lists that might be relevant
    conditions = [SharedReadingList.partner_id == checkout.partner_id]
    if program_id:
        conditions.append(SharedReadingList.program_id == program_id)

    lists_result = await db.execute(
        select(SharedReadingList)
        .where(*conditions)
        .options(selectinload(SharedReadingList.items))
        .limit(5)
    )
    lists = lists_result.scalars().unique().all()

    # Aggregate book recommendations
    all_books = []
    for reading_list in lists:
        for item in reading_list.items:
            all_books.append(
                {
                    "title": item.title,
                    "author": item.author,
                    "reading_level": item.reading_level,
                    "description": item.description,
                    "book_cover_url": item.book_cover_url,
                    "source_list": reading_list.name,
                }
            )

    return {
        "checkout_id": checkout_id,
        "classroom_name": checkout.classroom_name,
        "grade_level": checkout.grade_level,
        "reading_lists_found": len(lists),
        "recommended_books": all_books[:25],  # Limit to 25 recommendations
        "total_recommendations": len(all_books),
    }


