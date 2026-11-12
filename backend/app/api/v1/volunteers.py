# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive Volunteer Management API Endpoints

Provides endpoints for:
- Volunteer application and onboarding
- Background check tracking
- Training completion records
- Shift scheduling and sign-up
- Hour logging and verification
- Recognition milestones
- Skill matching to opportunities
- Volunteer appreciation tracking
"""
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.user import User, UserRole
from ...models.volunteer import (
    AppreciationRecord, BackgroundCheck,
    ShiftSignup, SkillMatch,
    SkillOpportunity, TrainingRecord, TrainingType, Volunteer,
    VolunteerApplication, VolunteerApplicationStatus,
    GeneralVolunteerHourLog, HourLogStatus,
    VolunteerMilestone, VolunteerShift, VolunteerSkill, VolunteerRoleCategory
)
from ...services.volunteer_service import (
    AppreciationService, BackgroundCheckService,
    HourLogService, MilestoneService,
    ShiftService, SkillMatchingService,
    TrainingService, VolunteerApplicationService,
    VolunteerProfileService
)
from .auth import get_current_user
from .dependencies import require_authenticated, require_staff
from .dependencies import require_staff
from fastapi import Depends

router = APIRouter(prefix="/volunteers", tags=["volunteers"])


# ============================================================================
# Volunteer Application Endpoints
# ============================================================================

# Public-form interest labels -> VolunteerRoleCategory values. preferred_roles
# feeds Volunteer.primary_role_category on approval, which is a DB enum.
INTEREST_TO_ROLE_CATEGORY = {
    "Shelving & Sorting": "shelving",
    "Event Support": "programming",
    "Storytime Helper": "programming",
    "Reading Buddy": "reader_advisory",
    "Tech Help": "tech_support",
    "Outreach & Delivery": "community_outreach",
    "Garden & Grounds": "other",
    "Translation": "patron_services",
    "Special Projects": "other",
}


class VolunteerApplyRequest(BaseModel):
    """Accepts both the model's field names and the public /volunteer/apply
    form's names (interests/availability/skills/phone/address). The form's
    identity fields (first_name/last_name/email) are ignored — the applicant
    is the authenticated user. Extra keys are ignored, never splatted into
    the ORM model (the raw-dict passthrough 500'd every real submission)."""

    why_volunteer: str = Field(min_length=1)
    background_check_consent: bool
    preferred_roles: List[str] = []
    interests: List[str] = []  # form alias for preferred_roles
    preferred_days: List[str] = []
    availability: Optional[str] = None  # form alias: "Weekday mornings; Evenings"
    availability_hours_per_week: int = Field(default=0, ge=0)
    previous_volunteer_experience: Optional[str] = None
    volunteer_start_date: Optional[date] = None
    expected_duration_months: Optional[int] = None
    can_drive: bool = False
    has_vehicle: bool = False
    references_provided: bool = False
    # Form-only fields with no model column: preserved for reviewers by
    # appending to why_volunteer below, so nothing a patron typed is lost.
    skills: List[str] = []
    phone: Optional[str] = None
    address: Optional[str] = None

    def to_model_kwargs(self) -> dict:
        # Approval feeds preferred_roles[0] into Volunteer.primary_role_category,
        # a DB enum — translate form labels to canonical slugs, keep valid slugs.
        valid_roles = {category.value for category in VolunteerRoleCategory}
        raw_roles = self.preferred_roles or self.interests
        mapped_roles = list(dict.fromkeys(
            role if role in valid_roles
            else INTEREST_TO_ROLE_CATEGORY.get(role, "other")
            for role in raw_roles
        ))
        why = self.why_volunteer.strip()
        extras = []
        if self.skills:
            extras.append("Skills: " + ", ".join(self.skills))
        if self.phone:
            extras.append("Phone: " + self.phone.strip())
        if self.address:
            extras.append("Address: " + self.address.strip())
        if mapped_roles != raw_roles:
            extras.append("Interests: " + ", ".join(raw_roles))
        if extras:
            why = why + "\n\n[From application form]\n" + "\n".join(extras)
        return {
            "why_volunteer": why,
            "background_check_consent": self.background_check_consent,
            "preferred_roles": mapped_roles,
            "preferred_days": self.preferred_days or [
                part.strip()
                for part in (self.availability or "").split(";")
                if part.strip()
            ],
            "availability_hours_per_week": self.availability_hours_per_week,
            "previous_volunteer_experience": self.previous_volunteer_experience,
            "volunteer_start_date": self.volunteer_start_date,
            "expected_duration_months": self.expected_duration_months,
            "can_drive": self.can_drive,
            "has_vehicle": self.has_vehicle,
            "references_provided": self.references_provided,
        }


@router.post("/apply", status_code=status.HTTP_201_CREATED)
async def apply_as_volunteer(
    application_data: VolunteerApplyRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Submit a volunteer application."""
    try:
        application = await VolunteerApplicationService.submit_application(
            db=db,
            user_id=current_user.id,
            application_data=application_data.to_model_kwargs()
        )
        return {
            "id": application.id,
            "status": application.status,
            "submitted_at": application.submitted_at,
            "message": "Application started. Complete and submit when ready."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/apply/submit/{application_id}")
async def submit_application_for_review(
    application_id: int,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Submit volunteer application for review."""
    try:
        # Verify user owns the application
        result = await db.execute(
            select(VolunteerApplication)
            .where(VolunteerApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application or application.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your application")

        application = await VolunteerApplicationService.submit_application_for_review(
            db=db,
            application_id=application_id
        )
        return {
            "id": application.id,
            "status": application.status,
            "submitted_at": application.submitted_at,
            "message": "Application submitted for review"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


async def _get_current_volunteer(
    current_user: User,
    db: AsyncSession,
) -> Optional[Volunteer]:
    volunteer = await VolunteerProfileService.get_volunteer_by_user(
        db=db,
        user_id=current_user.id,
    )
    if not volunteer:
        return None
    result = await db.execute(
        select(Volunteer).where(Volunteer.id == volunteer.id)
    )
    return result.scalar_one_or_none()


@router.get("/me")
async def get_my_volunteer_profile(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's volunteer profile. Returns 204 No Content if none."""
    volunteer = await _get_current_volunteer(current_user, db)
    if not volunteer:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return {
        "id": volunteer.id,
        "name": f"{current_user.first_name or ''} {current_user.last_name or ''}".strip(),
        "status": volunteer.status,
        "primary_role_category": volunteer.primary_role_category,
        "total_hours": volunteer.total_hours,
        "total_shifts": volunteer.total_shifts,
        "last_active_at": volunteer.last_active_at,
        "joined_at": volunteer.approved_at,
        "phone": volunteer.phone,
        "max_hours_per_week": volunteer.max_hours_per_week,
    }


# ============================================================================
# /me/* Aliases — current-user shortcuts that delegate to the underlying logic
# ============================================================================

@router.get("/me/milestones")
async def get_my_milestones(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's volunteer milestones (empty list if no profile)."""
    volunteer = await _get_current_volunteer(current_user, db)
    if not volunteer:
        return []
    result = await db.execute(
        select(VolunteerMilestone)
        .where(VolunteerMilestone.volunteer_id == volunteer.id)
        .order_by(VolunteerMilestone.achieved_at.desc())
    )
    milestones = result.scalars().all()
    return [
        {
            "id": m.id,
            "milestone_type": m.milestone_type,
            "achievement_value": m.achievement_value,
            "achieved_at": m.achieved_at,
            "celebration_message": m.celebration_message,
        }
        for m in milestones
    ]


@router.get("/me/hours")
async def get_my_hours(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's volunteer hour logs."""
    volunteer = await _get_current_volunteer(current_user, db)
    if not volunteer:
        return {"logs": [], "total_verified_hours": 0, "pending_hours": 0}
    result = await db.execute(
        select(GeneralVolunteerHourLog)
        .where(GeneralVolunteerHourLog.volunteer_id == volunteer.id)
        .order_by(GeneralVolunteerHourLog.log_date.desc())
    )
    logs = result.scalars().all()
    total_hours = sum(log.hours for log in logs if log.status == "verified")
    pending_hours = sum(log.hours for log in logs if log.status == "submitted")
    return {
        "logs": [
            {
                "id": log.id,
                "date": log.log_date,
                "hours": log.hours,
                "activity_type": log.activity_type,
                "status": log.status,
            }
            for log in logs
        ],
        "total_verified_hours": total_hours,
        "pending_hours": pending_hours,
    }


@router.get("/me/hours/summary")
async def get_my_hours_summary(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get summary of current user's volunteer hours."""
    volunteer = await _get_current_volunteer(current_user, db)
    if not volunteer:
        return {"total_verified_hours": 0, "pending_hours": 0, "total_shifts": 0}
    result = await db.execute(
        select(GeneralVolunteerHourLog)
        .where(GeneralVolunteerHourLog.volunteer_id == volunteer.id)
    )
    logs = result.scalars().all()
    return {
        "total_verified_hours": sum(log.hours for log in logs if log.status == "verified"),
        "pending_hours": sum(log.hours for log in logs if log.status == "submitted"),
        "total_shifts": volunteer.total_shifts or 0,
    }


@router.get("/me/shifts")
async def get_my_shifts(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's shift signups (with shift details)."""
    volunteer = await _get_current_volunteer(current_user, db)
    if not volunteer:
        return []
    result = await db.execute(
        select(ShiftSignup)
        .where(ShiftSignup.volunteer_id == volunteer.id)
        .options(selectinload(ShiftSignup.shift))
        .order_by(ShiftSignup.signed_up_at.desc())
    )
    signups = result.scalars().all()
    return [
        {
            "id": s.id,
            "shift_id": s.shift_id,
            "status": s.status,
            "signed_up_at": s.signed_up_at,
            "confirmed_at": s.confirmed_at,
            "checked_in_at": s.checked_in_at,
            "checked_out_at": s.checked_out_at,
            "actual_hours": s.actual_hours,
            "shift": {
                "id": s.shift.id,
                "title": s.shift.title,
                "description": s.shift.description,
                "shift_date": s.shift.shift_date,
                "start_time": s.shift.start_time,
                "end_time": s.shift.end_time,
                "location": s.shift.location,
            } if s.shift else None,
        }
        for s in signups
    ]


@router.get("/me/training")
async def get_my_training(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's training records."""
    volunteer = await _get_current_volunteer(current_user, db)
    if not volunteer:
        return []
    result = await db.execute(
        select(TrainingRecord)
        .options(selectinload(TrainingRecord.training_type))
        .where(TrainingRecord.volunteer_id == volunteer.id)
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "training_type_id": r.training_type_id,
            "training_type": r.training_type.name if r.training_type else None,
            "status": r.status,
            "completed_at": r.completed_at,
            "expires_at": r.expires_at,
        }
        for r in records
    ]


@router.get("/me/skills")
async def get_my_skills(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's volunteer skills."""
    volunteer = await _get_current_volunteer(current_user, db)
    if not volunteer:
        return []
    result = await db.execute(
        select(VolunteerSkill)
        .where(VolunteerSkill.volunteer_id == volunteer.id)
    )
    skills = result.scalars().all()
    return [
        {
            "id": s.id,
            "skill_name": s.skill_name,
            "proficiency_level": s.proficiency_level,
            "years_of_experience": s.years_of_experience,
            "description": s.description,
            "verified": s.verified,
        }
        for s in skills
    ]


@router.get("/me/skill-matches")
async def get_my_skill_matches(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's skill-matched opportunities."""
    volunteer = await _get_current_volunteer(current_user, db)
    if not volunteer:
        return []
    matches = await SkillMatchingService.match_volunteer_to_opportunities(
        db=db,
        volunteer_id=volunteer.id,
    )
    return [
        {
            "id": m.id,
            "opportunity_id": m.opportunity_id,
            "match_score": m.match_score,
            "matched_skills": m.matched_skills,
            "missing_skills": m.missing_skills,
        }
        for m in matches
    ]


@router.get("/me/appreciation")
async def get_my_appreciation(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's appreciation history."""
    volunteer = await _get_current_volunteer(current_user, db)
    if not volunteer:
        return []
    result = await db.execute(
        select(AppreciationRecord)
        .where(AppreciationRecord.volunteer_id == volunteer.id)
        .order_by(AppreciationRecord.given_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "appreciation_type": r.appreciation_type,
            "description": r.description,
            "reason": r.reason,
            "given_at": r.given_at,
            "made_public": r.made_public,
        }
        for r in records
    ]


# ============================================================================
# Staff-Only: Application Review
# ============================================================================

@router.get("/applications", dependencies=[Depends(require_staff)])
async def list_volunteer_applications(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List volunteer applications for staff review."""
    query = select(VolunteerApplication).options(selectinload(VolunteerApplication.user))

    if status:
        query = query.where(VolunteerApplication.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * limit
    query = query.order_by(VolunteerApplication.submitted_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    applications = result.scalars().all()

    return {
        "applications": [
            {
                "id": app.id,
                "user_id": app.user_id,
                "first_name": app.user.first_name if app.user else None,
                "last_name": app.user.last_name if app.user else None,
                "email": app.user.email if app.user else None,
                "status": app.status,
                "submitted_at": app.submitted_at,
                "preferred_roles": app.preferred_roles,
                "why_volunteer": app.why_volunteer,
                "availability_hours_per_week": app.availability_hours_per_week
            }
            for app in applications
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


class ApplicationReviewRequest(BaseModel):
    status: str
    review_notes: Optional[str] = None
    approval_data: Optional[dict] = None


@router.post("/applications/{app_id}/review", dependencies=[Depends(require_staff)])
async def review_application(
    app_id: int,
    payload: ApplicationReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Review volunteer application."""
    try:
        review_status = VolunteerApplicationStatus(payload.status)
        if review_status == VolunteerApplicationStatus.approved:
            application, volunteer = await VolunteerApplicationService.approve_and_create_profile(
                db=db,
                application_id=app_id,
                approver_id=current_user.id
            )
            return {
                "application_id": application.id,
                "volunteer_id": volunteer.id,
                "message": "Application approved and volunteer profile created"
            }
        else:
            application = await VolunteerApplicationService.review_application(
                db=db,
                application_id=app_id,
                reviewer_id=current_user.id,
                status=review_status,
                review_notes=payload.review_notes
            )
            return {
                "application_id": application.id,
                "status": application.status,
                "message": f"Application status updated to {review_status}"
            }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Background Check Endpoints
# ============================================================================

@router.post("/background-checks/{volunteer_id}", dependencies=[Depends(require_staff)])
async def initiate_background_check(
    volunteer_id: int,
    check_type: str = "criminal_record",
    provider_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Initiate background check for volunteer."""
    try:
        bg_check = await BackgroundCheckService.create_background_check(
            db=db,
            volunteer_id=volunteer_id,
            check_type=check_type
        )

        if provider_name:
            bg_check = await BackgroundCheckService.mark_check_in_progress(
                db=db,
                check_id=bg_check.id,
                provider_name=provider_name,
                provider_reference_id=f"REF-{bg_check.id}"
            )

        return {
            "id": bg_check.id,
            "volunteer_id": volunteer_id,
            "status": bg_check.status,
            "message": "Background check initiated"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{volunteer_id}/background-check")
async def get_background_check(
    volunteer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get background check status for volunteer."""
    result = await db.execute(
        select(BackgroundCheck)
        .where(BackgroundCheck.volunteer_id == volunteer_id)
    )
    bg_check = result.scalar_one_or_none()

    if not bg_check:
        return {"message": "No background check found"}

    return {
        "id": bg_check.id,
        "status": bg_check.status,
        "completed_at": bg_check.completed_at,
        "expires_at": bg_check.expires_at,
        "result_summary": bg_check.result_summary,
        "issues_found": bg_check.issues_found
    }


# ============================================================================
# Training Endpoints
# ============================================================================

@router.post("/{volunteer_id}/training/{training_type_id}", dependencies=[Depends(require_staff)])
async def assign_training(
    volunteer_id: int,
    training_type_id: int,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Assign training to volunteer."""
    try:
        training = await TrainingService.assign_training(
            db=db,
            volunteer_id=volunteer_id,
            training_type_id=training_type_id
        )
        return {
            "id": training.id,
            "volunteer_id": volunteer_id,
            "training_type_id": training_type_id,
            "status": training.status,
            "message": "Training assigned"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/{volunteer_id}/training/{training_id}/complete", dependencies=[Depends(require_staff)])
async def mark_training_complete(
    volunteer_id: int,
    training_id: int,
    trainer_id: Optional[int] = None,
    completion_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Mark training as completed."""
    try:
        training = await TrainingService.complete_training(
            db=db,
            training_id=training_id,
            trainer_id=trainer_id,
            completion_notes=completion_notes
        )
        return {
            "id": training.id,
            "status": training.status,
            "completed_at": training.completed_at,
            "message": "Training marked complete"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{volunteer_id}/training")
async def get_volunteer_training(
    volunteer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get volunteer's training records."""
    result = await db.execute(
        select(TrainingRecord)
        .where(TrainingRecord.volunteer_id == volunteer_id)
    )
    records = result.scalars().all()

    return [
        {
            "id": record.id,
            "training_type_id": record.training_type_id,
            "status": record.status,
            "completed_at": record.completed_at,
            "expires_at": record.expires_at
        }
        for record in records
    ]


# ============================================================================
# Shift Management Endpoints
# ============================================================================

class ShiftCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    role_category: str
    shift_date: date
    start_time: str
    end_time: str
    duration_hours: float = Field(gt=0)
    description: Optional[str] = None
    location: Optional[str] = None
    volunteers_needed: int = Field(default=1, ge=1)
    required_skills: List[str] = []


@router.post("/shifts", dependencies=[Depends(require_staff)])
async def create_shift(
    shift_data: ShiftCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a volunteer shift."""
    try:
        VolunteerRoleCategory(shift_data.role_category)  # 400 on junk, not a DB error
        shift = await ShiftService.create_shift(
            db=db,
            shift_data=shift_data.model_dump(),
            created_by_id=current_user.id
        )
        return {
            "id": shift.id,
            "title": shift.title,
            "shift_date": shift.shift_date,
            "volunteers_needed": shift.volunteers_needed,
            "message": "Shift created"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


def _serialize_shift(shift: VolunteerShift, *, staff: bool = False) -> dict:
    """Response shaping shared by the patron-facing /shifts list and the
    staff /shifts/staff list. Staff variant adds role_category + cancelled."""
    data = {
        "id": shift.id,
        "title": shift.title,
        "description": shift.description,
        "shift_date": shift.shift_date,
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "location": shift.location,
        "volunteers_needed": shift.volunteers_needed,
        "volunteers_signed_up": shift.volunteers_signed_up,
        "spots_available": max(0, shift.volunteers_needed - shift.volunteers_signed_up),
    }
    if staff:
        data["role_category"] = shift.role_category
        data["cancelled"] = bool(shift.cancelled)
    return data


def _validate_role_category(role_category: Optional[str]) -> None:
    if role_category is None:
        return
    try:
        VolunteerRoleCategory(role_category)  # 400 on junk, not a DB error
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/shifts")
async def list_available_shifts(
    role_category: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List available volunteer shifts."""
    _validate_role_category(role_category)

    # isnot(True), not == False: legacy/raw-inserted rows have NULL cancelled,
    # and NULL == False filters them out — every seeded shift was invisible.
    query = select(VolunteerShift).where(VolunteerShift.cancelled.isnot(True))

    if role_category:
        query = query.where(VolunteerShift.role_category == role_category)

    if from_date:
        query = query.where(VolunteerShift.shift_date >= from_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * limit
    query = query.order_by(VolunteerShift.shift_date).offset(offset).limit(limit)

    result = await db.execute(query)
    shifts = result.scalars().all()

    return {
        "shifts": [_serialize_shift(shift) for shift in shifts],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/shifts/staff", dependencies=[Depends(require_staff)])
async def list_shifts_staff(
    role_category: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    include_cancelled: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Staff shift list. Unlike the patron-facing /shifts, can optionally
    include cancelled shifts."""
    _validate_role_category(role_category)

    query = select(VolunteerShift)
    if not include_cancelled:
        query = query.where(VolunteerShift.cancelled.isnot(True))

    if role_category:
        query = query.where(VolunteerShift.role_category == role_category)

    if from_date:
        query = query.where(VolunteerShift.shift_date >= from_date)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * limit
    query = query.order_by(VolunteerShift.shift_date).offset(offset).limit(limit)

    result = await db.execute(query)
    shifts = result.scalars().all()

    return {
        "shifts": [_serialize_shift(shift, staff=True) for shift in shifts],
        "total": total,
        "page": page,
        "limit": limit,
    }


class ShiftUpdateRequest(BaseModel):
    """Partial update: only fields the staff UI actually sends are applied."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role_category: Optional[str] = None
    shift_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_hours: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = None
    location: Optional[str] = None
    volunteers_needed: Optional[int] = Field(default=None, ge=1)
    required_skills: Optional[List[str]] = None


@router.patch("/shifts/{shift_id}", dependencies=[Depends(require_staff)])
async def update_shift(
    shift_id: int,
    payload: ShiftUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Edit a volunteer shift (partial update)."""
    shift = await get_or_404(db, VolunteerShift, shift_id, "Shift not found")
    updates = payload.model_dump(exclude_unset=True)
    try:
        if "role_category" in updates:
            VolunteerRoleCategory(updates["role_category"])  # 400 on junk, not a DB error
        shift = await ShiftService.update_shift(db=db, shift=shift, updates=updates)
        return {
            "id": shift.id,
            "title": shift.title,
            "role_category": shift.role_category,
            "shift_date": shift.shift_date,
            "start_time": shift.start_time,
            "end_time": shift.end_time,
            "duration_hours": shift.duration_hours,
            "description": shift.description,
            "location": shift.location,
            "volunteers_needed": shift.volunteers_needed,
            "required_skills": shift.required_skills,
            "message": "Shift updated",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/shifts/{shift_id}/cancel", dependencies=[Depends(require_staff)])
async def cancel_shift(
    shift_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Soft-cancel a shift. Signups/history are kept; the patron-facing shift
    list hides it (cancelled.isnot(True))."""
    shift = await get_or_404(db, VolunteerShift, shift_id, "Shift not found")
    shift = await ShiftService.cancel_shift(db=db, shift=shift)
    return {
        "id": shift.id,
        "cancelled": shift.cancelled,
        "message": "Shift cancelled",
    }


@router.post("/shifts/{shift_id}/signup")
async def signup_for_shift(
    shift_id: int,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Sign up for a volunteer shift."""
    try:
        # Get volunteer profile (by user, NOT by primary key — ids diverge)
        volunteer = await _get_current_volunteer(current_user, db)
        if not volunteer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer profile not found")

        signup = await ShiftService.signup_for_shift(
            db=db,
            shift_id=shift_id,
            volunteer_id=volunteer.id
        )
        return {
            "signup_id": signup.id,
            "shift_id": shift_id,
            "status": signup.status,
            "message": "Successfully signed up for shift"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/signups/{signup_id}/confirm", dependencies=[Depends(require_staff)])
async def confirm_shift_signup(
    signup_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Confirm a shift signup."""
    try:
        signup = await ShiftService.confirm_signup(
            db=db,
            signup_id=signup_id
        )
        return {
            "signup_id": signup.id,
            "status": signup.status,
            "confirmed_at": signup.confirmed_at,
            "message": "Shift signup confirmed"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Hour Logging Endpoints
# ============================================================================

class HourLogRequest(BaseModel):
    log_date: date
    hours: float = Field(gt=0, le=24)
    activity_type: str
    description: Optional[str] = None
    shift_signup_id: Optional[int] = None


@router.post("/{volunteer_id}/hours/log")
async def log_volunteer_hours(
    volunteer_id: int,
    log_data: HourLogRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Log volunteer hours."""
    try:
        # Verify permission (volunteer or staff)
        volunteer = await VolunteerProfileService.get_volunteer_profile(db, volunteer_id)
        if not volunteer or (volunteer.user_id != current_user.id and current_user.role != UserRole.STAFF):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        hour_log = await HourLogService.log_hours(
            db=db,
            volunteer_id=volunteer_id,
            log_date=log_data.log_date,
            hours=log_data.hours,
            activity_type=log_data.activity_type,
            description=log_data.description,
            shift_signup_id=log_data.shift_signup_id,
        )
        return {
            "id": hour_log.id,
            "volunteer_id": volunteer_id,
            "hours": hour_log.hours,
            "status": hour_log.status,
            "message": "Hours logged successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/hour-logs", dependencies=[Depends(require_staff)])
async def list_hour_logs_queue(
    status_filter: str = Query("submitted", alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Cross-volunteer hour-log queue for staff review, joined to the
    volunteer's user record so staff know whose hours they're looking at."""
    try:
        HourLogStatus(status_filter)  # 400 on junk, not a DB error
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    query = (
        select(GeneralVolunteerHourLog)
        .options(selectinload(GeneralVolunteerHourLog.volunteer).selectinload(Volunteer.user))
        .where(GeneralVolunteerHourLog.status == status_filter)
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * limit
    query = query.order_by(GeneralVolunteerHourLog.log_date.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "hour_logs": [
            {
                "id": log.id,
                "volunteer_id": log.volunteer_id,
                "volunteer_name": (
                    f"{log.volunteer.user.first_name or ''} {log.volunteer.user.last_name or ''}".strip()
                    if log.volunteer and log.volunteer.user else None
                ),
                "log_date": log.log_date,
                "hours": log.hours,
                "activity_type": log.activity_type,
                "description": log.description,
                "status": log.status,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


class VerifyHoursRequest(BaseModel):
    verification_notes: Optional[str] = None


@router.post("/hour-logs/{log_id}/verify", dependencies=[Depends(require_staff)])
async def verify_hours(
    log_id: int,
    payload: Optional[VerifyHoursRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify volunteer hours."""
    try:
        hour_log = await HourLogService.verify_hours(
            db=db,
            log_id=log_id,
            verifier_id=current_user.id,
            verification_notes=payload.verification_notes if payload else None
        )
        return {
            "id": hour_log.id,
            "status": hour_log.status,
            "verified_at": hour_log.verified_at,
            "message": "Hours verified successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


class RejectHourLogRequest(BaseModel):
    reason: str = Field(min_length=1)


@router.post("/hour-logs/{log_id}/reject", dependencies=[Depends(require_staff)])
async def reject_hours(
    log_id: int,
    payload: RejectHourLogRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a submitted hour log. Requires a reason; does not touch
    Volunteer.total_hours (only verify does)."""
    log = await get_or_404(db, GeneralVolunteerHourLog, log_id, "Hour log not found")
    if log.status != HourLogStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only submitted hour logs can be rejected (current status: {log.status})",
        )
    log = await HourLogService.reject_hours(
        db=db, log=log, reason=payload.reason, rejector_id=current_user.id
    )
    return {
        "id": log.id,
        "status": log.status,
        "rejected_reason": log.rejected_reason,
        "rejected_at": log.rejected_at,
        "message": "Hours rejected",
    }


@router.get("/{volunteer_id}/hours")
async def get_volunteer_hours(
    volunteer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get volunteer hour logs."""
    result = await db.execute(
        select(GeneralVolunteerHourLog)
        .where(GeneralVolunteerHourLog.volunteer_id == volunteer_id)
        .order_by(GeneralVolunteerHourLog.log_date.desc())
    )
    logs = result.scalars().all()

    total_hours = sum(log.hours for log in logs if log.status == "verified")
    pending_hours = sum(log.hours for log in logs if log.status == "submitted")

    return {
        "logs": [
            {
                "id": log.id,
                "date": log.log_date,
                "hours": log.hours,
                "activity_type": log.activity_type,
                "status": log.status
            }
            for log in logs
        ],
        "total_verified_hours": total_hours,
        "pending_hours": pending_hours
    }


# ============================================================================
# Skill Management Endpoints
# ============================================================================

class AddSkillRequest(BaseModel):
    skill_name: str = Field(min_length=1, max_length=255)
    proficiency_level: str = "intermediate"
    years_of_experience: Optional[float] = None
    description: Optional[str] = None


@router.post("/{volunteer_id}/skills")
async def add_volunteer_skill(
    volunteer_id: int,
    skill_data: AddSkillRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Add skill to volunteer profile."""
    # Non-staff can only update their own skills
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        from ...models.volunteer import Volunteer
        result = await db.execute(select(Volunteer).where(Volunteer.id == volunteer_id))
        vol = result.scalar_one_or_none()
        if not vol or vol.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    try:
        skill = await SkillMatchingService.add_volunteer_skill(
            db=db,
            volunteer_id=volunteer_id,
            skill_name=skill_data.skill_name,
            proficiency_level=skill_data.proficiency_level,
            years_of_experience=skill_data.years_of_experience,
            description=skill_data.description,
        )
        return {
            "id": skill.id,
            "skill_name": skill.skill_name,
            "proficiency_level": skill.proficiency_level,
            "message": "Skill added"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{volunteer_id}/skill-matches")
async def get_skill_matches(
    volunteer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get skill-matched opportunities for volunteer."""
    matches = await SkillMatchingService.match_volunteer_to_opportunities(
        db=db,
        volunteer_id=volunteer_id
    )

    return [
        {
            "id": match.id,
            "opportunity_id": match.opportunity_id,
            "match_score": match.match_score,
            "matched_skills": match.matched_skills,
            "missing_skills": match.missing_skills
        }
        for match in matches
    ]


# ============================================================================
# Milestones & Recognition Endpoints
# ============================================================================

@router.get("/{volunteer_id}/milestones")
async def get_volunteer_milestones(
    volunteer_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get volunteer milestone achievements."""
    result = await db.execute(
        select(VolunteerMilestone)
        .where(VolunteerMilestone.volunteer_id == volunteer_id)
        .order_by(VolunteerMilestone.achieved_at.desc())
    )
    milestones = result.scalars().all()

    return [
        {
            "id": milestone.id,
            "milestone_type": milestone.milestone_type,
            "achievement_value": milestone.achievement_value,
            "achieved_at": milestone.achieved_at,
            "celebration_message": milestone.celebration_message
        }
        for milestone in milestones
    ]


# ============================================================================
# Appreciation Tracking Endpoints
# ============================================================================

@router.post("/{volunteer_id}/appreciation", dependencies=[Depends(require_staff)])
async def record_appreciation(
    volunteer_id: int,
    appreciation_type: str,
    description: str,
    reason: Optional[str] = None,
    occasion: Optional[str] = None,
    made_public: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record appreciation for volunteer."""
    try:
        record = await AppreciationService.record_appreciation(
            db=db,
            volunteer_id=volunteer_id,
            appreciation_type=appreciation_type,
            description=description,
            given_by_id=current_user.id,
            reason=reason,
            occasion=occasion,
            made_public=made_public
        )
        return {
            "id": record.id,
            "volunteer_id": volunteer_id,
            "appreciation_type": appreciation_type,
            "given_at": record.given_at,
            "message": "Appreciation recorded"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{volunteer_id}/appreciation")
async def get_volunteer_appreciation(
    volunteer_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get appreciation history for volunteer."""
    result = await db.execute(
        select(AppreciationRecord)
        .where(AppreciationRecord.volunteer_id == volunteer_id)
        .order_by(AppreciationRecord.given_at.desc())
    )
    records = result.scalars().all()

    return [
        {
            "id": record.id,
            "appreciation_type": record.appreciation_type,
            "description": record.description,
            "reason": record.reason,
            "given_at": record.given_at,
            "made_public": record.made_public
        }
        for record in records
    ]


# ============================================================================
# Configuration Endpoints
# ============================================================================

class VolunteerRoleOption(BaseModel):
    key: str
    label: str
    description: str


class SkillLevelOption(BaseModel):
    key: str
    label: str
    description: str


@router.get("/config/roles", response_model=List[VolunteerRoleOption])
async def get_volunteer_roles(
    current_user: User = Depends(require_authenticated),
):
    """Get list of available volunteer role options for form population."""
    role_descriptions = {
        "delivery": "Deliver library materials to home delivery patrons",
        "programming": "Assist with library programs and events",
        "tech_support": "Help patrons with technology and digital resources",
        "shelving": "Shelve returned materials and maintain collection organization",
        "reader_advisory": "Provide reading recommendations and book suggestions",
        "administrative": "Assist with office tasks and administrative support",
        "patron_services": "Help patrons at service desks and answer questions",
        "community_outreach": "Engage with the community and promote library services",
        "cataloging": "Help catalog and process new materials",
        "makerspace": "Assist patrons in makerspaces and with creative technology",
        "other": "Other volunteer opportunities"
    }

    return [
        VolunteerRoleOption(
            key=role.value,
            label=role.value.replace("_", " ").title(),
            description=role_descriptions.get(role.value, "")
        )
        for role in VolunteerRoleCategory
    ]


@router.get("/config/skill-levels", response_model=List[SkillLevelOption])
async def get_skill_levels(
    current_user: User = Depends(require_authenticated),
):
    """Get list of available skill proficiency levels for form population."""
    levels = [
        SkillLevelOption(
            key="beginner",
            label="Beginner",
            description="Just starting out, learning the basics"
        ),
        SkillLevelOption(
            key="intermediate",
            label="Intermediate",
            description="Comfortable with fundamentals, growing experience"
        ),
        SkillLevelOption(
            key="advanced",
            label="Advanced",
            description="Strong proficiency, can work independently"
        ),
        SkillLevelOption(
            key="expert",
            label="Expert",
            description="Mastery level, can mentor others"
        ),
    ]

    return levels


# ============================================================================
# Program Overview & Active Volunteers (Staff)
# ============================================================================

@router.get("/program/overview", dependencies=[Depends(require_staff)])
async def get_volunteer_program_overview(
    db: AsyncSession = Depends(get_db),
):
    """Get volunteer program overview stats for staff dashboard."""
    active_count = (await db.execute(
        select(func.count()).select_from(
            select(Volunteer).where(Volunteer.status == "active").subquery()
        )
    )).scalar_one()

    pending_count = (await db.execute(
        select(func.count()).select_from(
            select(VolunteerApplication).where(
                VolunteerApplication.status.in_(["submitted", "under_review"])
            ).subquery()
        )
    )).scalar_one()

    first_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_hours = (await db.execute(
        select(func.coalesce(func.sum(GeneralVolunteerHourLog.hours), 0)).where(
            GeneralVolunteerHourLog.log_date >= first_of_month.date()
        )
    )).scalar_one()

    return {
        "active_volunteers": active_count,
        "pending_applications": pending_count,
        "total_hours_this_month": float(monthly_hours),
    }


@router.get("/roster", dependencies=[Depends(require_staff)])
async def list_active_volunteers(
    db: AsyncSession = Depends(get_db),
):
    """List all volunteers with user info for staff roster view."""
    query = (
        select(Volunteer)
        .options(selectinload(Volunteer.user))
        .order_by(Volunteer.last_active_at.desc().nullslast())
    )
    result = await db.execute(query)
    volunteers = result.scalars().all()

    return {
        "volunteers": [
            {
                "id": v.id,
                "user_id": v.user_id,
                "first_name": v.user.first_name if v.user else None,
                "last_name": v.user.last_name if v.user else None,
                "email": v.user.email if v.user else None,
                "status": v.status,
                "primary_role_category": v.primary_role_category,
                "total_hours": v.total_hours,
                "total_shifts": v.total_shifts,
                "last_active_at": v.last_active_at,
                "start_date": v.start_date,
            }
            for v in volunteers
        ],
    }
