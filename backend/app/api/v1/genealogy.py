# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Genealogy API Endpoints.

Provides endpoints for:
- Genealogy research inquiries
- Training course management and enrollment
- Community archive submissions
- Public genealogy resources
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.genealogy import (
    CommunityArchiveSubmission,
    CourseEnrollment,
    GenealogyInquiry,
    GenealogyTrainingCourse,
    ResearchTopics,
)
from ...models.user import User, UserRole
from ...schemas.genealogy import (
    CommunityArchiveSubmissionCreate,
    CommunityArchiveSubmissionPublic,
    CommunityArchiveSubmissionResponse,
    CommunityArchiveSubmissionUpdate,
    CourseEnrollmentCreate,
    CourseEnrollmentResponse,
    GenealogyDashboard,
    GenealogyInquiryCreate,
    GenealogyInquiryResponse,
    GenealogyInquirySummary,
    GenealogyTrainingCourseCreate,
    GenealogyTrainingCoursePublic,
    GenealogyTrainingCourseResponse,
    GenealogyTrainingCourseUpdate,
)
from .auth import get_current_user, get_current_user_optional
from .dependencies import require_staff
from app.core.datetime_utils import utc_now

router = APIRouter(prefix="/genealogy", tags=["genealogy"])


# ============ GENEALOGY INQUIRIES ============


@router.post("/inquiries", response_model=GenealogyInquiryResponse, status_code=status.HTTP_201_CREATED)
async def create_genealogy_inquiry(  # noqa: role-check -- public genealogy inquiry, optional auth
    inquiry_data: GenealogyInquiryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Submit a genealogy research inquiry."""
    inquiry = GenealogyInquiry(
        user_id=current_user.id if current_user else None,
        first_name=inquiry_data.first_name,
        last_name=inquiry_data.last_name,
        email=inquiry_data.email,
        phone=inquiry_data.phone,
        preferred_contact=inquiry_data.preferred_contact,
        research_topic=inquiry_data.research_topic,
        description=inquiry_data.description,
        current_challenges=inquiry_data.current_challenges,
        status="new",
    )
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    return inquiry


@router.get("/inquiries", response_model=List[GenealogyInquirySummary])
async def list_genealogy_inquiries(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List genealogy inquiries (staff only)."""
    await require_staff(current_user)

    query = select(GenealogyInquiry)
    if status:
        query = query.where(GenealogyInquiry.status == status)

    query = query.order_by(desc(GenealogyInquiry.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/inquiries/{inquiry_id}", response_model=GenealogyInquiryResponse)
async def get_genealogy_inquiry(
    inquiry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get genealogy inquiry details (staff only)."""
    await require_staff(current_user)

    inquiry = await get_or_404(db, GenealogyInquiry, inquiry_id, "Inquiry not found")
    return inquiry


@router.put("/inquiries/{inquiry_id}", response_model=GenealogyInquiryResponse)
async def update_genealogy_inquiry(
    inquiry_id: int,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update genealogy inquiry response (staff only)."""
    await require_staff(current_user)

    inquiry = await get_or_404(db, GenealogyInquiry, inquiry_id, "Inquiry not found")

    if "response_from_genealogist" in update_data:
        inquiry.response_from_genealogist = update_data["response_from_genealogist"]
        inquiry.status = "responded"
        inquiry.responded_at = utc_now()
        inquiry.responded_by = current_user.id

    if "status" in update_data:
        inquiry.status = update_data["status"]

    await db.commit()
    await db.refresh(inquiry)
    return inquiry


# ============ TRAINING COURSES ============


@router.get("/courses", response_model=List[GenealogyTrainingCoursePublic])
async def list_genealogy_courses(
    level: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List available genealogy training courses (public)."""
    query = select(GenealogyTrainingCourse).where(
        GenealogyTrainingCourse.is_active == True
    )

    if level:
        query = query.where(GenealogyTrainingCourse.difficulty_level == level)

    query = query.order_by(GenealogyTrainingCourse.title)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/courses/{course_id}", response_model=GenealogyTrainingCourseResponse)
async def get_genealogy_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get genealogy course details."""
    course = await get_or_404(db, GenealogyTrainingCourse, course_id, "Course not found")
    return course


@router.post("/courses", response_model=GenealogyTrainingCourseResponse, status_code=status.HTTP_201_CREATED)
async def create_genealogy_course(
    course_data: GenealogyTrainingCourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create genealogy training course (staff only)."""
    await require_staff(current_user)

    course = GenealogyTrainingCourse(**course_data.model_dump())
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.put("/courses/{course_id}", response_model=GenealogyTrainingCourseResponse)
async def update_genealogy_course(
    course_id: int,
    course_data: GenealogyTrainingCourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update genealogy training course (staff only)."""
    await require_staff(current_user)

    course = await get_or_404(db, GenealogyTrainingCourse, course_id, "Course not found")

    update_data = course_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    await db.commit()
    await db.refresh(course)
    return course


# ============ COURSE ENROLLMENT ============


@router.post("/enrollment", response_model=CourseEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_in_course(
    enrollment_data: CourseEnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enroll user in genealogy training course."""
    # Check if course exists
    course_result = await db.execute(
        select(GenealogyTrainingCourse).where(
            GenealogyTrainingCourse.id == enrollment_data.course_id
        )
    )
    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check if already enrolled
    existing = await db.execute(
        select(CourseEnrollment).where(
            and_(
                CourseEnrollment.user_id == current_user.id,
                CourseEnrollment.course_id == enrollment_data.course_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course"
        )

    enrollment = CourseEnrollment(
        user_id=current_user.id,
        course_id=enrollment_data.course_id,
        status="registered",
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@router.get("/my-enrollments", response_model=List[CourseEnrollmentResponse])
async def get_my_course_enrollments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's course enrollments."""
    result = await db.execute(
        select(CourseEnrollment)
        .where(CourseEnrollment.user_id == current_user.id)
        .order_by(desc(CourseEnrollment.enrolled_at))
    )
    return result.scalars().all()


# ============ COMMUNITY ARCHIVES ============


@router.post("/archives/submit", response_model=CommunityArchiveSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_archive_item(  # noqa: role-check -- public community archive submission, optional auth
    submission_data: CommunityArchiveSubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Submit material to community archives. Auto-published; staff can hide."""
    submission = CommunityArchiveSubmission(
        user_id=current_user.id if current_user else None,
        **submission_data.model_dump()
    )
    submission.status = "published"
    submission.published_at = utc_now()
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


@router.get("/archives/public", response_model=List[CommunityArchiveSubmissionPublic])
async def list_public_archives(
    material_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List published community archive submissions (public)."""
    query = select(CommunityArchiveSubmission).where(
        and_(
            CommunityArchiveSubmission.status == "published",
            CommunityArchiveSubmission.is_public == True,
        )
    )

    if material_type:
        query = query.where(CommunityArchiveSubmission.material_type == material_type)

    if location:
        safe_location = location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            CommunityArchiveSubmission.location.ilike(f"%{safe_location}%")
        )

    query = query.order_by(
        desc(CommunityArchiveSubmission.published_at)
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/archives/submissions", response_model=List[CommunityArchiveSubmissionResponse])
async def list_archive_submissions(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List archive submissions for review (staff only)."""
    await require_staff(current_user)

    query = select(CommunityArchiveSubmission)
    if status:
        query = query.where(CommunityArchiveSubmission.status == status)

    query = query.order_by(
        desc(CommunityArchiveSubmission.id)
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/archives/{submission_id}", response_model=CommunityArchiveSubmissionResponse)
async def get_archive_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get archive submission details."""
    result = await db.execute(
        select(CommunityArchiveSubmission).where(
            CommunityArchiveSubmission.id == submission_id
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    # Check access permissions
    if submission.status != "published" and submission.access_level == "private":
        if not current_user or not await require_staff(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    return submission


@router.put("/archives/{submission_id}", response_model=CommunityArchiveSubmissionResponse)
async def update_archive_submission(
    submission_id: int,
    update_data: CommunityArchiveSubmissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update archive submission review (staff only)."""
    await require_staff(current_user)

    result = await db.execute(
        select(CommunityArchiveSubmission).where(
            CommunityArchiveSubmission.id == submission_id
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    if update_data.status:
        submission.status = update_data.status
        submission.reviewed_by = current_user.id
        submission.reviewed_at = utc_now()

        if update_data.status == "published":
            submission.published_at = utc_now()

    if update_data.review_notes:
        submission.review_notes = update_data.review_notes

    await db.commit()
    await db.refresh(submission)
    return submission


@router.patch("/archives/{submission_id}/hide", response_model=CommunityArchiveSubmissionResponse)
async def hide_archive_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hide an archive submission from public view (staff only)."""
    await require_staff(current_user)

    result = await db.execute(
        select(CommunityArchiveSubmission).where(
            CommunityArchiveSubmission.id == submission_id
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    submission.status = "hidden"
    submission.reviewed_by = current_user.id
    submission.reviewed_at = utc_now()

    await db.commit()
    await db.refresh(submission)
    return submission


# ============ DASHBOARD ============


@router.get("/dashboard", response_model=GenealogyDashboard)
async def get_genealogy_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """Get genealogy resources dashboard (public)."""
    # Count active courses
    courses_result = await db.execute(
        select(func.count(GenealogyTrainingCourse.id)).where(
            GenealogyTrainingCourse.is_active == True
        )
    )
    active_courses = courses_result.scalar() or 0

    # Count pending inquiries
    inquiries_result = await db.execute(
        select(func.count(GenealogyInquiry.id)).where(
            GenealogyInquiry.status == "new"
        )
    )
    pending_inquiries = inquiries_result.scalar() or 0

    # Count published submissions
    submissions_result = await db.execute(
        select(func.count(CommunityArchiveSubmission.id)).where(
            CommunityArchiveSubmission.status == "published"
        )
    )
    published_submissions = submissions_result.scalar() or 0

    # Get latest courses
    courses_query = select(GenealogyTrainingCourse).where(
        GenealogyTrainingCourse.is_active == True
    ).order_by(desc(GenealogyTrainingCourse.created_at)).limit(3)
    courses_result = await db.execute(courses_query)
    latest_courses = courses_result.scalars().all()

    # Get latest submissions
    submissions_query = select(CommunityArchiveSubmission).where(
        and_(
            CommunityArchiveSubmission.status == "published",
            CommunityArchiveSubmission.is_public == True,
        )
    ).order_by(desc(CommunityArchiveSubmission.published_at)).limit(3)
    submissions_result = await db.execute(submissions_query)
    latest_submissions = submissions_result.scalars().all()

    return GenealogyDashboard(
        active_courses=active_courses,
        pending_inquiries=pending_inquiries,
        published_submissions=published_submissions,
        latest_courses=latest_courses,
        latest_submissions=latest_submissions,
    )
